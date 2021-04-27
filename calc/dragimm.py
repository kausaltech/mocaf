import numpy as np
from .dragfilter import DragFilter
from .IMM import IMMEstimator
from scipy.linalg import expm

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

# TODO: Estimate "force and drag" from data!
filters = {
    'still': get_filter(1.0, 1.0),
    'walking': get_filter(2.0, 0.5),
    'cycling': get_filter(3.0, 0.3),
    'driving': get_filter(3.5, 0.3),
}

filter_idx = {k: i for i, k in enumerate(filters)}

N_states = len(filters)

# Just a rough guess of how long a "leg" lasts on average to
# compute the transition rate matrix.
mean_state_duration = 30*60

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
    
    most_likely_state = np.argmax(path_probs)
    most_likely_path = [most_likely_state]
    for states in most_likely_transitions[::-1]:
        most_likely_state = states[most_likely_state]
        most_likely_path.append(most_likely_state)
    
    most_likely_path = most_likely_path[::-1][1:]
    return np.array(ms), np.array(Ss), state_probs, most_likely_path


