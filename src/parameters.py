#!/usr/bin/env python

# defines global parameters to be used by the various parts of this programm

# Sound parameters
SND_SPEED           = 1500      # average speed of sound (m/s)
SND_VAR             = 0.01      # standard deviation for the speed of sound randomization

# Simulation parameters
SIM_RANGE           = 1000      # maximum range a transmission can reach (m)
SIM_LOSS            = 0         # probability of a transmission not being received (0-1)
SIM_TICK            = 0.1       # duration between two activations of the nodes (s)

# UPS localization parameters
UPS_PERIOD          = 1         # duration between two successive beacon cycles (s)
UPS_NUMBER          = 10        # number of localization cycles
