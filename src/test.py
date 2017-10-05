#!/usr/bin/env python

import parameters

parameters.SIM_LOSS = 0
parameters.SND_VAR = 0.02
parameters.TOA_ITERMAX = 20

# modify parameters BEFORE importing anything that depends on it

from SimEnvironment import SimEnvironment, distance
from rls import RLSNode
from lsls import LSLSNode
from ups import MasterAnchorNode, AnchorNode, SensorNode
from rls import RLSNode
from lst import LSTNode

from PositionCalculator import UPSCalculator, TOACalculator, TDOACalculator

from random import uniform, gauss
import matplotlib.pyplot as plt
import numpy as np


# RLS TEST

D = 4000  # side of the simulation area
L = 400   # distance between two node

sim = SimEnvironment((D, D, 500))

# add initial anchors

anchors = [ (D/2 - L, D/2 - L, 0)
          , (D/2 + L, D/2 - L, 0)
          , (D/2,     D/2 + L, 0)
          # , (D/2, D/2 + L, -300)
          ]

for n, p in enumerate(anchors):
	node = LSTNode(n, p, True)
	sim.addNode(node)

n = len(sim.nodes)

R = D/L

# add sensor nodes

for i in xrange(R):
	for j in xrange(R):
		x = (0.5 + i) * L
		y = (0.5 + j) * L
		z = -300
		# give nodes a random position around their theoretical placement
		idealPosition = np.array([x, y, z])
		realPosition = np.random.normal(idealPosition, 50)
		node = LSTNode(n, realPosition, False)
		node.positionEstimate = idealPosition # use the theoretical position as starting point for ToA
		sim.addNode(node)
		n += 1

# run the simulation (logging on, show begining and end)

sim.run(3000, show=3000, verbose=True)

# log the results

for n in sim.nodes:
	print n.name + "   \t" + n.status[0]
	ap = np.array(n.position)
	print " actual position     " + str(ap)
	ep = np.array(n.positionEstimate)
	d = np.linalg.norm(ap - ep)
	print " estimated position  " + str(ep)
	print " error               " + str(d)

print ""
print "TOA localization"
print "minimum   ", min        (LSTNode.toaDataY)
print "median    ", np.median  (LSTNode.toaDataY)
print "maximum   ", max        (LSTNode.toaDataY)
print "average   ", np.average (LSTNode.toaDataY)
print "variance  ", np.var     (LSTNode.toaDataY)

print ""
print "TDOA localization"
print "minimum   ", min        (LSTNode.tdoaDataY)
print "median    ", np.median  (LSTNode.tdoaDataY)
print "maximum   ", max        (LSTNode.tdoaDataY)
print "average   ", np.average (LSTNode.tdoaDataY)
print "variance  ", np.var     (LSTNode.tdoaDataY)

# display the gathered data

fig = plt.figure()
axes = fig.add_subplot(111)

axes.scatter(LSTNode.toaDataX, LSTNode.toaDataY, color='r', lw=0)
axes.scatter(LSTNode.tdoaDataX, LSTNode.tdoaDataY, color='b', lw=0)

plt.show()

# RLS tests

## TEST 1
# 10x10 nodes + 4 starting anchors
# ends in 11008 s (3 hr)
# 1750 transmissions total:
#  100  "position"
#   76  "anchor"
#  124  "request"
#  816  "beacon"    123 cycles initiated, 99 completed
#   72  "ping"
#  562  "ack"       ~ 7-8 ack per ping
#
# TOA equivalent (only 3 starting anchors)
#  103  "position"
#  100  "ping"
#  800  "ack"       approximately
# 1003 transmissions total

## TEST 2
# 20x20 nodes + 4 starting anchors
# ends in 83234 s (23 hr)
# 6418 transmissions total:
#  400  "position"
#  292  "anchor"
#  446  "request"
# 2835  "beacon"    446 cycles initiated, 341 completed
#  288  "ping"
# 2157  "ack"       ~ 7-8 ack per ping
#
# TOA equivalent (only 3 starting anchors)
#  403  "position"
#  400  "ping"
# 3200  "ack"       approximately
# 4003 transmissions total

# TEST 3
# 10x10 nodes + 4 starting anchors, 10 times
# duration      15378   7690    10384   8306    12256   14338   12048   11214   7680    12464   -   7680/11176/15378 (2/3/4 hr)
# "position"    100     100     100     100     100     100     100     100     100     100     -   100/100/100
# "anchor"      81      72      74      74      75      77      72      78      73      77      -   72/75/81
# "request"     122     84      101     78      149     133     112     101     81      134     -   78/110/149
# "beacon"      746     623     660     561     960     834     755     674     599     903     -   561/732/960
# "ping"        77      68      70      70      71      73      68      74      69      73      -   68/71/77
# "ack"         602     478     517     513     547     571     501     551     505     587     -   478/537/602
# total         1728    1425    1522    1396    1902    1788    1608    1578    1427    1874    -   1396/1625/1902

# ups-related	942/100 = 9.42
# toa-related	679/71 = 9.56

# TEST 4
# 20x20 nodes + 4 starting anchors, dense
# ends in 49328 s (14 hr)
# 3443 transmissions total
#  396 "position"
#  119 "anchor"
#  175 "request"
# 1366 "beacon"
#  115 "ping"
# 1272 "ack"

# missing 20 22 23 385

# ups-related	1937/396 = 4.89
# toa-related	1502/115 = 13.06

## EMPIRICAL FINDINGS
# TDOA for a network of N nodes:
# 1.00 N    "position"
# 0.75 N    "anchor"
# 1.25 N    "request"
# 7.50 N    "beacon"
# 0.75 N    "ping"
# 5.50 N    "ack"
# 16.75 N total
#
# TOA for a network of N nodes:
# 1.00 N    "position"
# 1.00 N    "ping"
# 8.00 N    "ack"
# 10.00 N total

# LST tests

# TEST 1
# 4x4 km, 10x10 nodes
# ends in 1880 s (31 mn)
#  100 "positionn"  1.0
#  100 "call"       1.0
#  548 "reply"      5.48
#  748 total        7.48

# TEST 2
# 2x2 km, 10x10 nodes
# ends in 672 s (11 mn)
#  100 "position"   1.0
#  100 "call"       1.0
#  997 "reply"      9.97
# 1197 total       11.97

# TEST 3
# 4x4 km, 20x20 nodes
# ends in 5704 s (1 hr 35 mn)
#  400 "position"   1.0
#  400 "call"       1.0
# 4616 "reply"     11.54
# 5416 total       13.54