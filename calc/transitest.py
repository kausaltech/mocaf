from scipy.interpolate import interp1d
import numpy as np
from scipy.stats import norm

def transit_likelihoods(leg, transits):
    leg_t = leg.time.values
    leg_pos = leg[['x', 'y']].values
    trans_liks = {}
    for key, transit in transits.items():
        if len(transit) < 2:
            trans_liks[key] = np.nan
            continue
        transit_t = transit.time.values
        transit_pos = transit[['x', 'y']].values
        transit_pos = interp1d(transit_t, transit_pos, axis=0, bounds_error=False)(leg_t)
        diffs = leg_pos - transit_pos
        dists = np.linalg.norm(diffs, axis=1)
        # TODO MEGAHACK: Using negative mean distances as "likelihoods".
        # so the API is for maximizing instead of minimizing
        trans_liks[key] = -np.median(dists)
    
    return trans_liks

def transit_prob_ests_shit(leg, transits, transit_loc_std=10.0):
    # Just a precision weighted average distance of leg location points from linearly
    # interpolated transit locations with some stetson-harrison to come up with a
    # probabilistish confidence. Not statistically rigorous, but a decent hack to avoid
    # heuristics too early.
    #
    # We have no estimates of transit location measurement error, so just
    # stetson-harrison something in transit_loc_std. API would be cleaner if
    # the calling code would just inpute this when it's not available and this
    # function would work purely with distributions. We also have linearization/discretization
    # error that is now bundled in the same noise distribution, but this could be enhanced
    # by taking into account this error
    leg_t = leg.time.values
    leg_pos = leg[['x', 'y']].values
    trans_shit = {}
    for key, transit in transits.items():
        if len(transit) < 2:
            trans_shit[key] = np.nan
            continue
        transit_t = transit.time.values
        transit_pos = transit[['x', 'y']].values
        # DRAGON ALERT! This may cause weird corner cases if there are vehicles 
        transit_pos = interp1d(transit_t, transit_pos, axis=0, fill_value='extrapolate')(leg_t)
        diffs = leg_pos - transit_pos
        leg_pos_var = leg['location_std'].values**2
        dists = np.linalg.norm(diffs, axis=1)
        error_vars = transit_loc_std**2 + leg_pos_var**2 # TODO: Verify this?
        precisions = 1/error_vars
        weights = precisions/np.sum(precisions)

        est_mean_dist = dists@weights
        # Negative meters, TOTAL HACK!!
        trans_shit[key] = -est_mean_dist
    return trans_shit

def is_transit_wild_guess_will_break(leg, transits):
    trans_shit = transit_prob_ests_shit(leg, transits)
    best_hit = max(trans_shit.values())
    HARDCODED_HACK_HEURISTIC_YÖK = -30 # Negative meters, TOTAL HACK!!
    
    return best_hit > HARDCODED_HACK_HEURISTIC_YÖK



def transit_likelihoods_(leg, transits, transit_loc_std=10.0):

    leg_t = leg.time.values
    leg_pos = leg[['x', 'y']].values
    leg_pos_var = leg[['location_std']]**2
    trans_liks = {}
    for key, transit in transits.items():
        if len(transit) < 2:
            trans_liks[key] = np.nan
            continue
        transit_t = transit.time.values
        transit_pos = transit[['x', 'y']].values
        transit_pos = interp1d(transit_t, transit_pos, axis=0, bounds_error=False)(leg_t)
        diffs = leg_pos - transit_pos
        error_vars = transit_loc_std**2 + leg_pos_var**2 # TODO: Verify this?
        
        # Could do this with a chi^2 distribution, as we have spherical error,
        # but I find it conceptually cleaner this way
        diff_distr = scipy.stats.multivariate_normal(0, error_vars)
        diff_logliks = diff_distr.logpdf(diffs)
        
        loglik = np.sum(diff_logliks)
        
        trans_liks[key] = loglik
        #dists = np.linalg.norm(diffs, axis=1)

        # TODO MEGAHACK: Using negative mean distances as "likelihoods".
        # so the API is for maximizing instead of minimizing
    
    return trans_liks
