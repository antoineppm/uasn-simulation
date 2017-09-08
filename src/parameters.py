#!/usr/bin/env python

# defines global parameters to be used by the various parts of this programm

# Sound parameters
SND_SPEED           = 1500.     # average speed of sound (m/s)
SND_VAR             = 0.01      # standard deviation for the speed of sound randomization

# Simulation parameters
SIM_RANGE           = 1000.     # maximum range a transmission can reach (m)
SIM_LOSS            = 0.        # probability of a transmission not being received (0-1)
SIM_TICK            = 0.1       # duration between two activations of the nodes (s)

# UPS localization parameters
UPS_PERIOD          = 1.        # duration between two successive beacon cycles (s)
UPS_NUMBER          = 10        # number of localization cycles

# LSLS parameters
LSLS_WAITFACTOR     = 10.       # "K" factor for waiting periods
LSLS_SUBRANGE       = 500.      # secondary range for anchor selection
LSLS_TOLERANCE      = 5.        # maximum error estimate to consider a node localized

# RLS parameters
RLS_TIMESLOT        = 2.        # length of a node's assigned time slot (s)
RLS_TOLERANCE       = 5.        # maximum error for a position estimate to be taken into account


# TOA calculation parameters
TOA_ITERMAX         = 10        # maximum number of iterations of the Gauss-Newton method
TOA_THRESHOLD       = 0.01      # variation threshold to stop the Gauss-Newton method