#!/usr/bin/env python

from SimEnvironment import SimEnvironment
from UWNode import UWNode

class AnchorNode(UWNode):
	"""Node that knows its position and takes par in the beaconing sequence"""
	def __init__(self, priority, position):
		"""Create an anchor node
		priority    -- indicates the beaconing order
		            the anchor with priority 0 beacons first, followed by 1, etc
		position    -- X,Y,Z coordinates of the anchor node (m,m,m)
		"""
		name = "anchor" + str(priority)
		UWNode.__init__(self, name, position)
		self.priority = priority
		self.timeOfReception = 0				# used to calculate the beaconing delay
		self.nextToBeacon = False				# set to True after receiving the beacon from the previous anchor
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the anchor node is next in line to beacon, sends out a message: position + beaconing delay
		"""
		if self.priority == 0 and time == 0:
			print str(self.name) + " initating beaconing sequence"
			x, y, z = self.position
			return "0 " + str(x) + " " + str(y) + " " + str(z) + " 0"
		elif self.nextToBeacon:
			print str(self.name) + " beaconing at time " + str(time)
			self.nextToBeacon = False
			x, y, z = self.position
			delay = time - self.timeOfReception
			return str(self.priority) + " " + str(x) + " " + str(y) + " " + str(z) + " " + str(delay)
		else:
			return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		priority = int(message.split()[0])
		if priority + 1 == self.priority:
			print str(self.name) + " received beacon " + str(priority) + " at time " + str(time)
			self.timeOfReception = time
			self.nextToBeacon = True

sim = SimEnvironment((500,500,200))

sim.addNode(AnchorNode(0, (0, 0, 0)))
sim.addNode(AnchorNode(1, (0, 500, 0)))
sim.addNode(AnchorNode(2, (500, 250, 0)))
sim.addNode(AnchorNode(3, (250, 250, 200)))

sim.run(2)
	
	