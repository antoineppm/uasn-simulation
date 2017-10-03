#!/usr/bin/env python

from parameters import *
from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from PositionCalculator import UPSCalculator

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
		Never transmits
		"""
		priority = int(message.split()[1])
		if priority + 1 == self.priority:
			# print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon: " + message
			self.beaconCount = int(message.split()[0])
			x, y, z, delay = [ float(i) for i in message.split()[2:6] ]
			if self.distanceToPrevious is None:
				self.distanceToPrevious = distance(self.position, (x,y,z))
			self.timeOrigin = time - (self.distanceToPrevious / SND_SPEED) - delay
		return ""
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		plot.scatter(x, y, z, c='k', marker='s')

class MasterAnchorNode(AnchorNode):
	"""Anchor node that initiates the beaconing sequences"""
	def __init__(self, position):
		AnchorNode.__init__(self, 0, position)
		self.nextBeaconTime = 0
		self.beaconCount = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the anchor node is next in line to beacon, sends out a message: position + beaconing delay
		"""
		message = ""
		if time >= self.nextBeaconTime and self.beaconCount < UPS_NUMBER:
			self.timeOrigin = time      # we set the origin as the time of beaconing of the master
			message = AnchorNode.tick(self, time)
			self.nextBeaconTime += UPS_PERIOD
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
		self.calculator = UPSCalculator()
		self.timeout = float('inf')
		self.positionEstimate = None
		# self.errorEstimate = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the sensor has received all four beacons, calculates and log its position
		Never transmits
		"""
		if time >= self.timeout:
			error, position = self.calculator.getPosition()
			if error != "ok":
				print self.name + " could not find its position: " + error
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
			else:
				x, y, z = position
				print self.name + " found position: " + "%.3f, %.3f, %.3f" % (x, y, z)
				print "       actual position: " + "%.3f, %.3f, %.3f" % self.position
				print "                 error: " + "%.3f" % distance(self.position, position)
				# print "        error estimate: " + "%.3f" % e
				self.positionEstimate = position
				# self.errorEstimate = e
			self.timeout = float('inf')
		return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		Never transmits
		"""
		# print "{:6}".format("%.3f" % time) + " -- " + self.name + " received beacon: " + message
		beaconCount = int(message.split()[0])
		anchor = int(message.split()[1])
		x, y, z, delay = [ float(i) for i in message.split()[2:6] ]
		self.calculator.addAnchor(anchor, (x, y, z))
		self.calculator.addDataPoint(anchor, beaconCount, (time, delay))
		self.timeout = time + 5        # arbitrary 5-second timeout
		return ""
	
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
			# plot.scatter(ex, ey, ez, c=(0,0,1,0.2), marker='o', lw=0, s=50*self.errorEstimate)
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
