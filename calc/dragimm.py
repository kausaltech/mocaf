import numpy as np
from .dragfilter import DragFilter
from .IMM import IMMEstimator
from scipy.linalg import expm
import numba

# Just some very uninformative priors,
# the mean is somewhere around central Tampere.
# This essentially assumes that they are somewhere
# around Scandinavia. In practice this won't matter much
# as the measurement variance will be miniscule compared
# to this. Could probably use infinite initial variance
# just as well, but it requires tweaks into the algorithm.
# Likely not worth the hassle.
x0 = 327673.1276769259
y0 = 6820919.330099265
m0 = np.array([x0, y0, 0.0, 0.0])

location_std = 1000.0
speed_std = 200.0
S0 = np.diag([location_std**2, location_std**2, speed_std**2, speed_std**2])

def get_filter(force, drag):
    # TODO: S0 for speeds can be inferred from the parameters, probably
    # doesn't matter.
    return lambda: DragFilter(force, drag, np.copy(m0), np.copy(S0))

# Median matched to speeds
filters = {
    'still': get_filter(0.5, 1.0),
    'walking': get_filter(2.0, 0.6),
    'cycling': get_filter(3.0, 0.06),
    'driving': get_filter(3.5, 0.008),
}

# Just some stetson-harrisons
"""
filters = {
    'still': get_filter(0.5, 1.0),
    'walking': get_filter(2.0, 0.5),
    'cycling': get_filter(3.0, 0.3),
    'driving': get_filter(3.5, 0.3),
}
"""

filter_idx = {k: i for i, k in enumerate(filters)}

N_states = len(filters)

# Just a rough guess of how long a "leg" lasts on average to
# compute the transition rate matrix.
mean_state_duration = 5*60

# A rough transition rate matrix assuming same mean duration
# and same transition probability
transition_rate = np.zeros((N_states, N_states)) + (1/mean_state_duration)/(N_states - 1)
transition_rate[np.diag_indices(N_states)] = -1/mean_state_duration

def filter_trajectory(traj):
    # TODO: Smoothing!
    filts = [f() for f in filters.values()]
    # TODO: Could use some global average. Probably doesn't matter
    state_probs = np.ones(N_states)
    state_probs /= np.sum(state_probs)

    initial_state_probs = np.copy(state_probs)
    # The trellis with a less confusing name.
    # Note that state_probs is different from path_probs.
    # The latter refers to sort of "maximum likelihood attainable by selecting
    # this state at this step". More or less standard Viterbi, but with the
    # IMM observation probs. Breaking quite a few assumptions here probably, so
    # not strictly optimal but probably works relatively well; IMM breaks them all already anyway.
    path_probs = np.copy(state_probs)
    most_likely_transitions = []
    
    imm = IMMEstimator(filts, state_probs)
    #imm = filts[-1] # HACK!
    
    ms = []
    Ss = []
    state_probs = []

    prev_time = None
    for z in traj:
        if prev_time is None:
            prev_time = z.time
        dt = z.time - prev_time
        prev_time = z.time
        # The transition matrix for this timestep. For some reason FilterPy has
        # this in the update step. I think it would be more logical in the prediction
        # step as this can be computed without any measurements. TODO: Verify FilterPy
        # implementation.
        M = expm(transition_rate*dt)
        
        with np.errstate(all="raise"):
            # Qd(dt) overflows when the dt is too high. Currently the Kalman filters
            # handle this. Would be nicer to handle here. Not sure what to do other
            # than revert to the initial mean and covariance. Infinite initial covariance would
            # make this cleaner.
            imm.predict(dt)

        measurement = np.array([z.x, z.y])
        
        R = float(z.location_std)
        if R <= 0:
            # There are some negative values, just input something for them.
            # Should be fixed at client end.
            R = 100.0
        
        # TODO: Check that this is correct. The location_std is the
        # 68% prob (ie std of) radius of the error
        R = np.diag([R**2, R**2])
        
        # Compute "external" predictions of the new state. We could fuse
        # also e.g. MEMS derived predictions here too.
        # TODO: Could really use the full prediction probability vector
        # here!!
        # TODO: Is there more succint way of computing the full prob vector like this?
        if z.atype is not None:
            mode_state_prob = z.aconf
            leftover_prob = (1 - mode_state_prob)/(N_states - 1)
            state_prob_ests = np.zeros(N_states) + leftover_prob
            state_prob_ests[filter_idx[z.atype]] = mode_state_prob
        else:
            state_prob_ests = None
        # TODO: Try to get the M into the prediction step. Mostly because
        # it feels wrong here.
        imm.update(measurement, R, M, state_prob_ests=state_prob_ests)
        ms.append(np.copy(imm.x))
        Ss.append(np.copy(imm.P))
        state_probs.append(np.copy(imm.mu))

        # Compute the most likely path stuff
        path_probs_new = np.empty_like(path_probs)
        new_transitions = []
        for new_mode_i in range(N_states):
            best_prev_i = None
            best_new_prob = -1
            for prev_mode_i in range(len(filters)):
                obs_lik = filts[new_mode_i].likelihood
                new_prob = path_probs[prev_mode_i]*obs_lik*M[prev_mode_i,new_mode_i]
                if new_prob > best_new_prob:
                    best_new_prob = new_prob
                    best_prev_i = prev_mode_i
            path_probs_new[new_mode_i] = best_new_prob
            new_transitions.append(best_prev_i)
        path_probs = path_probs_new
        path_probs /= np.sum(path_probs)
        most_likely_transitions.append(new_transitions)
    
    state_probs = np.array(state_probs)

    most_likely_state = np.argmax(path_probs)
    most_likely_path = [most_likely_state]
    for states in most_likely_transitions[::-1]:
        most_likely_state = states[most_likely_state]
        most_likely_path.append(most_likely_state)
    
    # TODO FIXME: This seems to be broken ATM! Fix or remove the duplicate viterbi-attempt
    most_likely_path = most_likely_path[::-1][1:]

    # TODO FIXME: Temporary hack as the viterbi is a bit buggy ATM
    #most_likely_path = np.argmax(state_probs, axis=1)
    
    # TODO FIXME: Hack to do "most likely path decoding" with IMM state probs. Theoretically HIDEOUS!
    # TODO FIXME: Known to cause problems that time-variant transition probs will fix easily!
    HACK_FIXED_DT_TRANSITIONS = expm(transition_rate*5)
    most_likely_path = viterbi(initial_state_probs, HACK_FIXED_DT_TRANSITIONS, state_probs)
    most_likely_path = np.array(most_likely_path)
    
    return np.array(ms), np.array(Ss), state_probs, most_likely_path, imm.total_loglikelihood


def safelog(x):
    return np.log(np.clip(x, 1e-9, None))

def viterbi(initial_probs, transition_probs, emissions):
    # TODO: Online mode
    # TODO: Variable dt transitions!!
    n_states = len(initial_probs)
    emissions = iter(emissions)
    emission = next(emissions)
    transition_probs = safelog(transition_probs)
    probs = safelog(emission) + safelog(initial_probs)
    state_stack = []
    
    for i, emission in enumerate(emissions):
        total_prob = np.sum(emission)
        if total_prob > 1e-9:
            emission /= total_prob
        else:
            emission[:] = 1/len(emission)
        trans_probs = transition_probs + np.row_stack(probs)
        most_likely_states = np.argmax(trans_probs, axis=0)
        probs = safelog(emission) + trans_probs[most_likely_states, np.arange(n_states)]
        state_stack.append(most_likely_states)
    
    state_seq = [np.argmax(probs)]

    while state_stack:
        most_likely_states = state_stack.pop()
        state_seq.append(most_likely_states[state_seq[-1]])

    state_seq.reverse()

    return state_seq
