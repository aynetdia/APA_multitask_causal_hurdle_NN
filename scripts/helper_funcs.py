import os
import random
import torch
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error


def set_seed():
    """
    Set all the necessary seeds to ensure replicability
    """
    os.environ['PYTHONHASHSEED'] = str(1)
    random.seed(2)
    np.random.seed(3)
    torch.manual_seed(4)
    torch.cuda.manual_seed_all(5)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def calc_prediction_error(prediction_dict, y_true, g, prob_treatment=None, tau_true=None):
    """
    Calculate the prediction error (TOL) of the model predictions
    prediction_dict : dict
        Dictionary with the model predictions in the form model_name: array of predictions
    y_true : 1D array-like
        Observed outcomes
    g : 1D array-like
        Binary group indicator
    prob_treatment : array-like or int
        The group propensity for each observation. If None or int, the constant probability
        to be in binary treatment group 1.
    tau_true : 1D array-like
        Array of the true treatment effect. The true treatment effect
        is only known in simulations
    """
    output = {}
    
    if prob_treatment is None:
        prob_treatment = g.mean()
    
    for model_name, pred in prediction_dict.items():
        output[model_name] = {}
        #pred.clip(-100,100)
        output[model_name]["transformed_outcome_loss"] = transformed_outcome_loss(tau_pred=pred, y_true=y_true, g=g, 
                                                                                  prob_treatment=prob_treatment)
        if tau_true is not None:
            output[model_name]["root_mean_squared_error"] = np.sqrt(mean_squared_error(y_pred=pred, y_true=tau_true))
            output[model_name]["mean_absolute_error"] = mean_absolute_error(y_pred=pred, y_true=tau_true)

    return output


def transformed_outcome_loss(tau_pred, y_true, g, prob_treatment):
    """
    Calculate a biased estimate of the mean squared error of individualized treatment effects

    tau_pred : array
        The predicted individualized treatment effects.
    y_true : array
        The observed individual outcome.
    g : array, {0,1}
        An indicator of the treatment group. Currently supports only two treatment groups, typically
        control (g=0) and treatment group (g=1).
    """
    # Transformed outcome
    y_trans = (g - prob_treatment)  * y_true / (prob_treatment * (1-prob_treatment))
    loss = np.mean(((y_trans - tau_pred)**2))
    return loss


def expected_policy_profit(targeting_decision, g, observed_profit, prob_treatment):
    """
    Calculate the profit of a coupon targeting campaign
    """
    return np.sum(((1-targeting_decision) * (1-g) * observed_profit)/(1-prob_treatment) +
                    (targeting_decision  *    g  * observed_profit)/(prob_treatment))


def bayesian_targeting_policy(tau_pred, contact_cost, offer_accept_prob, offer_cost, value=None):
    """
    Applied the Bayesian optimal decision framework to make a targeting decision.
    The decision to target is made when the expected profit increase from targeting is strictly
    larger than the expected cost of targeting.

    tau_pred : array-like
        Estimated treatment effect for each observations. Typically the effect on the expected profit.
        If tau_pred is the treatment effect on conversion, 'value' needs to be specified.

    contact_cost : float or array-like
        Static cost that realizes independent of outcome

    offer_cost : float or array-like
        Cost that realizes when the offer is accepted

    value : float or array-like, default: None
        Value of the observations in cases where tau_pred is the
        change in acceptance probability (binary outcome ITE)
    """
    if value:
        tau_pred = tau_pred * value

    return (tau_pred > (offer_accept_prob * offer_cost - contact_cost)).astype('int')

