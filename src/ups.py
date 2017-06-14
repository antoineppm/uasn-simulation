#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from math import sqrt
import numpy as np

beaconPeriod = 1        # time between two beacon cycles (s)
beaconNumber = 100       # number of beacon cycles

class AnchorNode(UWNode):
	"""Node that knows its position and takes part in the beaconing sequence"""
	def __init__(self, priority, position):
		"""Create an anchor node
		priority    -- indicates the beaconing order
		            the anchor with priority 0 beacons first, followed by 1, etc
		position    -- X,Y,Z coordinates of the anchor node (m,m,m)
		"""
		name = "anchor" + str(priority)
		UWNode.__init__(self, name, position)
		self.priority = priority
		self.beaconCount = -1                   # number of beacons already performed
		# used by master anchor (priority 0)
		self.nextBeaconTime = 0                 # time of next beacon
		# used by follower anchors (priority > 0)
		self.distanceToPrevious	= 0				# distance to the anchor immediately before
		self.timeOrigin = 0                     # used to calculate the beaconing delay
		self.nextBeacon = ""                    # indicates type of beacon to send at the next tick, if any
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the anchor node is next in line to beacon, sends out a message: position + beaconing delay
		"""
		message = ""
		if self.priority == 0 and time >= self.nextBeaconTime:
			if self.beaconCount == -1:
				x, y, z = self.position
				message = "0 position " + str(x) + " " + str(y) + " " + str(z)
			elif self.beaconCount < beaconNumber:
				message = "0 beacon " + str(self.beaconCount) + " 0"
			elif self.beaconCount == beaconNumber+1:	# we skip a cycle to give the previous beaconing cycle time to finish
				message = "0 done"
			self.nextBeaconTime += beaconPeriod
			self.beaconCount += 1
		elif self.priority > 0:
			if self.nextBeacon == "position":
				x, y, z = self.position
				message = str(self.priority) + " position " + str(x) + " " + str(y) + " " + str(z)
			elif self.nextBeacon == "beacon":
				delay = time - self.timeOrigin
				message = str(self.priority) + " beacon " + str(self.beaconCount) + " " + str(delay)
			self.nextBeacon = ""
		if len(message) > 0:
			print "{:6}".format("%.3f" % time) + " -- " + self.name + " sending: " + message
		return message
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		priority = int(message.split()[0])
		if priority + 1 == self.priority:
			print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon " + str(priority) + ": " + message
			self.nextBeacon = message.split()[1]
			if self.nextBeacon == "position":
				x, y, z = [ float(i) for i in message.split()[2:5] ]
				self.distanceToPrevious = distance(self.position, (x,y,z))
			elif self.nextBeacon == "beacon":
				self.beaconCount = int(message.split()[2])
				delay = float(message.split()[3])
				self.timeOrigin = time - (self.distanceToPrevious / self.speedOfSound) - delay

class SensorNode(UWNode):
	"""Node that does not know its position, and calculates it by listening to the beacons"""
	def __init__(self, nb):
		"""Create a sensor node with undefined position
		nb          -- numerical identifier used to name the node
		"""
		name = "sensor" + str(nb)
		UWNode.__init__(self, name)
		self.anchorPositions = [ None for i in xrange(4) ]      # will contain four positions (xi,yi,zi)
		self.receptionTimes =  []                               # will contain lists of four pairs (ti,dti)
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the sensor has received all four beacons, calculates and log its position
		Never transmits
		"""
		return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon: " + message
		anchor = int(message.split()[0])
		messageType = message.split()[1]
		if messageType == "position":
			x, y, z = [ float(i) for i in message.split()[2:5] ]
			self.anchorPositions[anchor] = (x,y,z)
		if messageType == "beacon":
			beaconCount = int(message.split()[2])
			delay = float(message.split()[3])
			while len(self.receptionTimes) <= beaconCount:
				self.receptionTimes.append([None, None, None, None])
			self.receptionTimes[beaconCount][anchor] = (time, delay)
		if messageType == "done":
			pos = self.multilaterate()
			if isinstance(pos, basestring):
				print self.name + " could not find its position: " + pos
			else:
				x,y,z = pos
				print self.name + " found position: " + "%.3f, %.3f, %.3f" % (x, y, z)
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
				print "                 error: " + "%.3f" % distance(self.position, (x,y,z))
	
	def multilaterate(self):
		"""Solves the equations to calculate the position of the node"""
		for anchor in self.anchorPositions:
			if anchor is None:
				return "missing anchors"
		x0, y0, z0 = self.anchorPositions[0]
		x1, y1, z1 = self.anchorPositions[1]
		x2, y2, z2 = self.anchorPositions[2]
		x3, y3, z3 = self.anchorPositions[3]
		# k coefficients
		k1List = []
		k2List = []
		k3List = []
		for beacon in self.receptionTimes:
			if beacon[0] is None:
				continue
			t0, dt0 = beacon[0]
			if beacon[1] is not None:
				t1, dt1 = beacon[1]
				k1List.append(t0 - dt0 - t1 + dt1)
			if beacon[2] is not None:
				t2, dt2 = beacon[2]
				k2List.append(t0 - dt0 - t2 + dt2)
			if beacon[3] is not None:
				t3, dt3 = beacon[3]
				k3List.append(t0 - dt0 - t3 + dt3)
		if len(k1List) == 0 or len(k2List) == 0 or len(k3List) == 0:
			return "not enough data"
		k1 = self.speedOfSound * sum(k1List) / len(k1List)
		k2 = self.speedOfSound * sum(k2List) / len(k2List)
		k3 = self.speedOfSound * sum(k3List) / len(k3List)
		# solving linear equations
		M = np.array([ [x0-x1,  y0-y1,  z0-z1],
		               [x0-x2,  y0-y2,  z0-z2],
		               [x0-x3,  y0-y3,  z0-z3] ])
		A = np.array([ -k1,
		               -k2,
		               -k3 ])
		B = np.array([ (k1*k1 + x0*x0 + y0*y0 + z0*z0 - x1*x1 - y1*y1 - z1*z1) / 2,
		               (k2*k2 + x0*x0 + y0*y0 + z0*z0 - x2*x2 - y2*y2 - z2*z2) / 2,
		               (k3*k3 + x0*x0 + y0*y0 + z0*z0 - x3*x3 - y3*y3 - z3*z3) / 2 ])
		Ax, Ay, Az = np.linalg.solve(M, A)
		Bx, By, Bz = np.linalg.solve(M, B)
		# solving quadtratic equation
		alpha = Ax*Ax + Ay*Ay + Az*Az - 1
		beta = 2 * (Ax*Bx + Ay*By + Az*Bz - x0*Ax - y0*Ay - z0*Az)
		gamma = Bx*Bx + By*By + Bz*Bz - 2 * (x0*Bx + y0*By + z0*Bz) + x0*x0 + y0*y0 + z0*z0
		delta = beta*beta - 4*alpha*gamma
		w = 0
		if delta < 0:
			return "no solution"
		elif delta == 0:
			w = -beta / (2*alpha)
		else:
			w1 = (-beta - sqrt(delta)) / (2*alpha)
			w2 = (-beta + sqrt(delta)) / (2*alpha)
			if w2 < 0:
				w = w1
			elif w1 < 0:
				w = w2
			else:
				return "two solutions"
		# calculating the coordinates
		x = Ax*w + Bx
		y = Ay*w + By
		z = Az*w + Bz
		return (x,y,z)
	

sim = SimEnvironment((500,500,200))

sim.addNode(AnchorNode(0, (0, 0, 0)))
sim.addNode(AnchorNode(1, (0, 500, 0)))
sim.addNode(AnchorNode(2, (500, 250, 0)))
sim.addNode(AnchorNode(3, (500, 250, -200)))

sensor = SensorNode(0)
sensor.position = (250,250,-100)

sim.addNode(sensor)

sim.run(200)
