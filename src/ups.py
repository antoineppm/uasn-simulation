#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from math import sqrt
import numpy as np

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
			print str(self.name) + " received beacon " + str(priority) + " at time " + str(time) + ": " + message
			self.timeOfReception = time
			self.nextToBeacon = True

class SensorNode(UWNode):
	"""Node that does not know its position, and calculates it by listening to the beacons"""
	def __init__(self, nb):
		"""Create a sensor node with undefined position
		nb          -- numerical identifier used to name the node
		"""
		name = "sensor" + str(nb)
		UWNode.__init__(self, name)
		self.beaconsReceived = []
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		If the sensor has received all four beacons, calculates and log its position
		Never transmits
		"""
		if len(self.beaconsReceived) == 4:
			pos = self.multilaterate()
			if pos is None:
				print self.name + " could not find its position"
			else:
				x,y,z = pos
				print self.name + " found position: " + str((x, y, z))
			print "actual position: " + str(self.position)
			self.beaconsReceived = []
		return ""
	
	def multilaterate(self):
		"""Solves the equations to calculate the position of the node"""
		# get parameters from the data received
		x0, y0, z0, t0, dt0 = self.beaconsReceived[0]
		x1, y1, z1, t1, dt1 = self.beaconsReceived[1]
		x2, y2, z2, t2, dt2 = self.beaconsReceived[2]
		x3, y3, z3, t3, dt3 = self.beaconsReceived[3]
		# distances between beacons
		dist01 = distance((x0,y0,z0),(x1,y1,z1))
		dist12 = distance((x1,y1,z1),(x2,y2,z2))
		dist23 = distance((x2,y2,z2),(x3,y3,z3))
		# k coefficients
		k1 = dist01 + (dt1 + t0 - t1) * self.speedOfSound
		k2 = dist01 + dist12 + (dt1 + dt2 + t0 - t2) * self.speedOfSound
		k3 = dist01 + dist12 + dist23 + (dt1 + dt2 + dt3 + t0 - t3) * self.speedOfSound
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
		delta = sqrt(beta*beta - 4*alpha*gamma)
		w1 = (-beta - delta) / (2*alpha)
		w2 = (-beta + delta) / (2*alpha)
		# calculating the coordinates
		w = 0
		if w1 == w2:
			w = w1
		elif w2 < 0:
			w = w1
		elif w1 < 0:
			w = w2
		else:
			return None		# no unique position can be determined
		x = Ax*w + Bx
		y = Ay*w + By
		z = Az*w + Bz
		return (x,y,z)
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		# print self.name + " received beacon at time " + str(time) + ": " + message
		priority, x, y, z, delay = [float(s) for s in message.split()]
		self.beaconsReceived.append((x, y, z, time, delay))

sim = SimEnvironment((500,500,200))

sim.addNode(AnchorNode(0, (0, 0, 0)))
sim.addNode(AnchorNode(1, (0, 500, 0)))
sim.addNode(AnchorNode(2, (500, 250, 0)))
sim.addNode(AnchorNode(3, (250, 250, -200)))

for i in xrange(20):
	sim.addNode(SensorNode(i))

sim.run(2)
