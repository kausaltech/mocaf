import numpy as np
import matplotlib.pyplot as plt
import numba
from numba import njit

# http://gregorygundersen.com/blog/2019/10/30/scipy-multivariate/
@njit(cache=True)
def mvnormlogpdf(x, mean, cov):
    # `eigh` assumes the matrix is Hermitian.
    vals, vecs = np.linalg.eigh(cov)
    logdet     = np.sum(np.log(vals))
    valsinv    = np.array([1./v for v in vals])
    # `vecs` is R times D while `vals` is a R-vector where R is the matrix 
    # rank. The asterisk performs element-wise multiplication.
    U          = vecs * np.sqrt(valsinv)
    rank       = len(vals)
    dev        = x - mean
    # "maha" for "Mahalanobis distance".
    maha       = np.square(np.dot(dev, U)).sum()
    log2pi     = np.log(2 * np.pi)
    return -0.5 * (rank * log2pi + maha + logdet)

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
@njit(cache=True)
def Qd(dt, force, drag):
    exp = np.exp
    return np.array([[dt*force/drag**2 - 3*force/(2*drag**3) + 2*force*exp(-drag*dt)/drag**3 - force*exp(-2*drag*dt)/(2*drag**3), 0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0], [0, dt*force/drag**2 - 3*force/(2*drag**3) + 2*force*exp(-drag*dt)/drag**3 - force*exp(-2*drag*dt)/(2*drag**3), 0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2)], [force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0, force/(2*drag) - force*exp(-2*drag*dt)/(2*drag), 0], [0, force*(exp(2*drag*dt) - 2*exp(drag*dt) + 1)*exp(-2*drag*dt)/(2*drag**2), 0, force/(2*drag) - force*exp(-2*drag*dt)/(2*drag)]])

# Sympy generated mess for solving expm(F*dt) for this case
@njit(cache=True)
def Fd(dt, force, drag):
    # See https://en.wikipedia.org/wiki/Discretization#Discretization_of_linear_state_space_models
    exp = np.exp
    Ft = np.array([[1, 0, 1/drag - exp(-drag*dt)/drag, 0], [0, 1, 0, 1/drag - exp(-drag*dt)/drag], [0, 0, exp(-drag*dt), 0], [0, 0, 0, exp(-drag*dt)]])
    return Ft

@njit(cache=True)
def predict(dt, m, S, Fd, Qd):
    m = Fd@m
    
    # See https://sci-hub.st/https://www.sciencedirect.com/science/article/pii/S0076539206800767
    # for solving the differential lypuanov equation that governs the covariance matrix.
    # No general analytical solution is known, but it's relatively simple to solve for
    # special cases. Here Qt should be the integral part of the known solution for a time-invariant
    # F.
    S = Fd@S@Fd.T + Qd
    
    return m, S

from numpy import dot
# Adapted from filterpy
@njit
def update(x, P, z, R, H):
    Hx = dot(H, x)
    #z = reshape_z(z, Hx.shape[0], x.ndim)

    # error (residual) between measurement and prediction
    y = z - Hx

    # project system uncertainty into measurement space
    S = dot(dot(H, P), H.T) + R


    # map system uncertainty into kalman gain
    K = dot(dot(P, H.T), np.linalg.inv(S))


    # predict new x with residual scaled by the kalman gain
    x = x + dot(K, y)

    # P = (I-KH)P(I-KH)' + KRK'
    KH = dot(K, H)

    I_KH = np.eye(KH.shape[0]) - KH
    P = dot(dot(I_KH, P), I_KH.T) + dot(dot(K, R), K.T)


    # compute log likelihood
    log_likelihood = mvnormlogpdf(z, dot(H, x), S)
    return x, P, y, K, S, log_likelihood
    #return x, P


class DragFilter:
    def __init__(self, force, drag, x, P):
        # Using filterpy conventions x for mean and P for covariance
        # TODO: We could compute the stationary x and P for speeds given force and drag
        self.force = force
        self.drag = drag
        self.x = x
        self.P = P


        # TODO: The measurement model doesn't currently use speed or bearing.
        # Need to derive the speed distributions (or approximations) from these, should
        # be straightforward. Not sure if this will effect anything much if the
        # speeds and bearings are just estimated from the samples. Measurement variance
        # is given in the measurements, so no need to assume values for that.
        self.H = np.array([
            [1.0, 0, 0, 0,],
            [0, 1.0, 0, 0,]
        ])

        self.likelihood = 1.0

    def predict(self, dt):
        # Hack to avoid over/underflows: cap "effective" dt to 300 seconds
        dt = min(dt, 300)
        Q = Qd(dt, self.force, self.drag)
        F = Fd(dt, self.force, self.drag)
        self.x, self.P = predict(dt, self.x, self.P, F, Q)

    def update(self, z, R):
        # Just a standard Kalman update with varying R
        # IMM needs the likelihood of the previous sample. This is
        # mostly computed in update below again, but optimize later
        
        predicted_z = self.H@self.x
        z_cov = self.H@self.P@self.H.T + R
        residual = z - predicted_z
        
        #print(residual)
        self.likelihood = np.exp(mvnormlogpdf(residual, 0.0, z_cov))
        self.likelihood = max(self.likelihood, float_eps)
        
        # TODO: Using this likelihood gives a different result than
        # the residual likelihood. Don't know the implications yet!
        self.x, self.P, y, K, S, loglik = update(self.x, self.P, z, R, self.H)
        #self.likelihood = np.exp(loglik)
        #self.likelihood = max(self.likelihood, float_eps)

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
        
