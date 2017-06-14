#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from TDOACalculator import TDOACalculator

beaconPeriod = 1        # time between two beacon cycles (s)
beaconNumber = 1        # number of beacon cycles

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
		self.tdoaCalc = TDOACalculator()
	
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
			self.tdoaCalc.addAnchor(anchor, x, y, z)
		if messageType == "beacon":
			beaconCount = int(message.split()[2])
			delay = float(message.split()[3])
			self.tdoaCalc.addDataPoint(beaconCount, anchor, time, delay)
		if messageType == "done":
			error, x, y, z = self.tdoaCalc.calculatePosition(self.speedOfSound)
			if error != "ok":
				print self.name + " could not find its position: " + error
			else:
				print self.name + " found position: " + "%.3f, %.3f, %.3f" % (x, y, z)
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
				print "                 error: " + "%.3f" % distance(self.position, (x,y,z))

sim = SimEnvironment((500,500,200), {"sigma":0})

sim.addNode(AnchorNode(0, (0, 0, 0)))
sim.addNode(AnchorNode(1, (0, 500, 0)))
sim.addNode(AnchorNode(2, (500, 250, 0)))
sim.addNode(AnchorNode(3, (500, 250, -200)))

sensor = SensorNode(0)
sensor.position = (250,250,-100)

sim.addNode(sensor)

sim.run(200)
