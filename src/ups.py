#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from TDOACalculator import TDOACalculator

class AnchorNode(UWNode):
	"""Node that knows its position and takes part in the beaconing sequence"""
	def __init__(self, priority, position):
		"""Create an anchor node
		priority    -- indicates the beaconing order (0-3)
		            the anchor with priority 0 beacons first, followed by 1, etc
		position    -- X,Y,Z coordinates of the anchor node (m,m,m)
		"""
		name = "anchor" + str(priority)
		UWNode.__init__(self, name, position)
		self.priority = priority
		self.beaconCount = 0                    # number of beacons already performed
		self.distanceToPrevious	= None          # distance to the anchor immediately before
		self.timeOrigin = None                  # used to calculate the beaconing delay; if None, no beacon
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the anchor node is next in line to beacon, sends out a message: position + beaconing delay
		"""
		message = ""
		if self.timeOrigin is not None:
			x, y, z = self.position
			delay = time - self.timeOrigin
			message = str(self.beaconCount) + " " + str(self.priority) + " " + str(x) + " " + str(y) + " " + str(z) + " " + str(delay)
			self.timeOrigin = None
			
		if len(message) > 0:
			print "{:6}".format("%.3f" % time) + " -- " + self.name + " sending: " + message
			pass
		return message
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		priority = int(message.split()[1])
		if priority + 1 == self.priority:
			# print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon: " + message
			self.beaconCount = int(message.split()[0])
			x, y, z, delay = [ float(i) for i in message.split()[2:6] ]
			if self.distanceToPrevious is None:
				self.distanceToPrevious = distance(self.position, (x,y,z))
			self.timeOrigin = time - (self.distanceToPrevious / self.speedOfSound) - delay
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		plot.scatter(x, y, z, c='k', marker='s')

class MasterAnchorNode(AnchorNode):
	"""Anchor node that initiates the beaconing sequences"""
	def __init__(self, position, beaconPeriod, beaconNumber):
		AnchorNode.__init__(self, 0, position)
		self.beaconPeriod = beaconPeriod
		self.nextBeaconTime = 0
		self.beaconNumber = beaconNumber
		self.beaconCount = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the anchor node is next in line to beacon, sends out a message: position + beaconing delay
		"""
		message = ""
		if time >= self.nextBeaconTime and self.beaconCount < self.beaconNumber:
			self.timeOrigin = time      # we set the origin as the time of beaconing of the master
			message = AnchorNode.tick(self, time)
			self.nextBeaconTime += self.beaconPeriod
			self.beaconCount += 1
		return message

class SensorNode(UWNode):
	"""Node that does not know its position, and calculates it by listening to the beacons"""
	def __init__(self, nb):
		"""Create a sensor node with undefined position
		nb          -- numerical identifier used to name the node
		"""
		name = "sensor" + str(nb)
		UWNode.__init__(self, name)
		self.tdoaCalc = TDOACalculator()
		self.timeout = float('inf')
		self.positionEstimate = None
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the sensor has received all four beacons, calculates and log its position
		Never transmits
		"""
		if time >= self.timeout:
			error, x, y, z = self.tdoaCalc.calculatePosition(self.speedOfSound)
			if error != "ok":
				print self.name + " could not find its position: " + error
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
			else:
				print self.name + " found position: " + "%.3f, %.3f, %.3f" % (x, y, z)
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
				print "                 error: " + "%.3f" % distance(self.position, (x,y,z))
				self.positionEstimate = (x,y,z)
			self.timeout = float('inf')
		return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		# print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon: " + message
		beaconCount = int(message.split()[0])
		anchor = int(message.split()[1])
		x, y, z, delay = [ float(i) for i in message.split()[2:6] ]
		self.tdoaCalc.addAnchor(anchor, x, y, z)
		self.tdoaCalc.addDataPoint(beaconCount, anchor, time, delay)
		self.timeout = time + 5        # arbitrary 5-second timeout
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		if self.positionEstimate is None:
			plot.scatter(x, y, z, c='r', marker='^', lw=0)
		else:
			ex, ey, ez = self.positionEstimate
			plot.scatter(x, y, z, c='b', marker='^', lw=0)
			plot.scatter(ex, ey, ez, c='k', marker='+')
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
