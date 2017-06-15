#!/usr/bin/env python

from SimEnvironment import SimEnvironment
from UWNode import UWNode

sim = SimEnvironment((500,500,200))

for i in xrange(20):
	sim.addNode(UWNode(str(i)))

sim.show()