#!/usr/bin/env python

from SimEnvironment import SimEnvironment
from UWNode import UWNode
from ups import AnchorNode, SensorNode

sim = SimEnvironment((500,500,200), {"sigma":0.01, "reliability":0.9})

sim.addNode(AnchorNode(0, (0, 0, 0)))
sim.addNode(AnchorNode(1, (0, 500, 0)))
sim.addNode(AnchorNode(2, (500, 250, 0)))
sim.addNode(AnchorNode(3, (500, 250, -200)))

for i in xrange(20):
	sim.addNode(SensorNode(i))

sim.run(200)

# for i in xrange(20):
# 	sim.addNode(UWNode(""))

sim.show()