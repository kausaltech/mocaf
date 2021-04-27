import numpy as np
import matplotlib.pyplot as plt
from filterpy.kalman import update
from scipy.linalg import expm
from filterpy.stats import logpdf as mvnormlogpdf

force = 2.0
drag = 0.01


F = np.array([
    [0.0,   0.0,    1.0,    0.0],
    [0.0,   0.0,    0.0,    1.0],
    [0.0,   0.0,    -drag, 0.0],
    [0.0,   0.0,    0.0, -drag],
])

Q = np.diag([0.0, 0.0, force**2, force**2])

# Just grand mean x and y from the dataset at the time
# of coding. Will not matter much.
x0 = 327673.1276769259
y0 = 6820919.330099265
m0 = np.array([x0, y0, 0.0, 0.0])

# Just some very uninformative priors,
# the mean is somewhere around central Tampere.
# This essentially assumes that they are somewhere
# around Scandinavia. In practice this won't matter much
# as the measurement variance will be miniscule compared
# to this. Could probably use infinite initial variance
# just as well, but it requires tweaks into the algorithm.
# Likely not worth the hassle.
location_std = 10000.0
speed_std = 200.0
S0 = np.diag([location_std**2, location_std**2, speed_std**2, speed_std**2])

# TODO: The measurement model doesn't currently use speed or bearing.
# Need to derive the speed distributions (or approximations) from these, should
# be straightforward. Not sure if this will effect anything much if the
# speeds and bearings are just estimated from the samples. Measurement variance
# is given in the measurements, so no need to assume values for that.
H = np.array([
    [1, 0, 0, 0,],
    [0, 1, 0, 0,]
    ])

float_eps = np.finfo(float).eps

# Sympy generated mess for solving the "Qd" for the Fc and Q above
def Qd(dt, force, drag):
    exp = np.exp
    return np.array([[dt*force/drag**2 - 3*force/(2*drag**3) + 2*force*exp(-drag*dt)/drag**3 - force*exp(-2*drag*dt)/(2*drag**3), 0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0], [0, dt*force/drag**2 - 3*force/(2*drag**3) + 2*force*exp(-drag*dt)/drag**3 - force*exp(-2*drag*dt)/(2*drag**3), 0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2)], [force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0, force/(2*drag) - force*exp(-2*drag*dt)/(2*drag), 0], [0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0, force/(2*drag) - force*exp(-2*drag*dt)/(2*drag)]])

def predict(dt, m, S, F, Qd):
    # TODO: Optimize later. Probably not necessary to take expms here, but
    # don't know if it's any slower than an explicit solution. But we can't use
    # a Python implementation in production anyway
    # See https://en.wikipedia.org/wiki/Discretization#Discretization_of_linear_state_space_models
    expFT = expm(F*dt)
    m = expFT@m
    
    # See https://sci-hub.st/https://www.sciencedirect.com/science/article/pii/S0076539206800767
    # for solving the differential lypuanov equation that governs the covariance matrix.
    # No general analytical solution is known, but it's relatively simple to solve for
    # special cases. Here Qt should be the integral part of the known solution for a time-invariant
    # F.
    S = expFT@S@expFT.T + Qd
    
    return m, S

class DragFilter:
    def __init__(self, force, drag, x, P):
        # Using filterpy conventions x for mean and P for covariance
        # TODO: We could compute the stationary x and P for speeds given force and drag
        self.force = force
        self.drag = drag
        self.x = x
        self.P = P
        self.F = np.array([
            [0.0,   0.0,    1.0,    0.0],
            [0.0,   0.0,    0.0,    1.0],
            [0.0,   0.0,    -drag, 0.0],
            [0.0,   0.0,    0.0, -drag],
        ])

        # TODO: The measurement model doesn't currently use speed or bearing.
        # Need to derive the speed distributions (or approximations) from these, should
        # be straightforward. Not sure if this will effect anything much if the
        # speeds and bearings are just estimated from the samples. Measurement variance
        # is given in the measurements, so no need to assume values for that.
        self.H = np.array([
            [1, 0, 0, 0,],
            [0, 1, 0, 0,]
        ])

        self.likelihood = 1.0

        # Stored here so we can revert if Q overflows. Try to find
        # a cleaner solution.
        self.x0 = np.copy(x)
        self.P0 = np.copy(P)


    def predict(self, dt):
        # Hack to avoid over/underflows: cap "effective" dt to 300 seconds
        dt = min(dt, 300)
        Q = Qd(dt, self.force, self.drag)
        self.x, self.P = predict(dt, self.x, self.P, self.F, Q)

    def update(self, z, R):
        # Just a standard Kalman update with varying R
        # IMM needs the likelihood of the previous sample. This is
        # mostly computed in update below again, but optimize later
        
        predicted_z = self.H@self.x
        z_cov = self.H@self.P@self.H.T + R
        residual = z - predicted_z
        
        self.likelihood = np.exp(mvnormlogpdf(x=residual, cov=z_cov))
        self.likelihood = max(self.likelihood, float_eps)
        self.x, self.P = update(self.x, self.P, z, R, self.H)


def filter_trajectory(traj):
    # TODO: Do smoothing!
    m = m0.copy()
    S = S0.copy()

    ms = []
    Ss = []

    prev_time = None
    for z in traj:
        if prev_time is None:
            prev_time = z.time
        dt = z.time - prev_time
        prev_time = z.time
        
        with np.errstate(all="raise"):
            # Qd(dt) overflows when the dt is too high. Just revert
            # to initial in these cases
            try:
                m, S = predict(dt, m, S, F, Qd(dt))
            except FloatingPointError:
                #m = m0.copy()
                S = S0.copy()

        measurement = np.array([z.x, z.y])
        
        R = float(z.location_std)
        if R <= 0:
            # There are some negative values, just input something for them.
            # Should be fixed at client end.
            R = 10.0
        
        # TODO: Check that this is correct. The location_std is the
        # 68% prob (ie std of) radius of the error
        R = np.diag([R**2, R**2])
        
        m, S = update(m, S, measurement, R, H)
        ms.append(m)
        Ss.append(S)

    return np.array(ms), np.array(Ss)
        
