#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from TDOACalculator import TDOACalculator

class LSLSNode(UWNode):
	"""All-purpose node localizing itself using the LSLS scheme"""
	def __init__(self, id, position = (-1,-1,0), localized = False):
		"""Create a node
		name        -- string identifying the node
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		name = "node" + "".join(str(id).split())    # making sure the name does not contain any whitespace
		UWNode.__init__(self, name, position)
		self.timer = float('inf')
		self.tdoaCalc = None
		self.master = None
		if localized:
			self.positionEstimate = position
			self.errorEstimate = 0
			self.status = "localized"
			self.level = 1
		else:
			self.positionEstimate = None
			self.errorEstimate = None
			self.status = "unlocalized"
			self.level = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		sp = message.split()
		sender = sp[0]
		subject = sp[1]
		data = sp[2:]
		if subject == "anchor":
			[level, x, y, z, parent] = data
			if self.status == "unlocalized":
				pass
			elif self.status == "localized" and level = self.level - 1:
				pass
			elif self.status == "candidate" and level = self.level:
				pass
			elif self.status == "confirming":
				pass
			elif self.status == "anchor":
				pass
		elif subject == "confirm":
			[f] = data
			if self.status == "unlocalized":
				pass
			elif self.status == "localized":
				pass
			elif self.status == "candidate":
				pass
			elif self.status == "confirming":
				pass
			elif self.status == "anchor":
				pass
		elif subject == "beacon":
			[count, level, delay] = data
			if self.status == "unlocalized":
				pass
			elif self.status == "localized":
				pass
			elif self.status == "candidate":
				pass
			elif self.status == "confirming":
				pass
			elif self.status == "anchor":
				pass
	
	def getCandidateTimer(self, d):
		k = 10      # must be adjusted for best performances
		r = self.simParams["range"]
		v = self.simParams["sos"]
		if self.level == 0:
			return k * (r - d) / v
		else:
			return k * (r - 4*d + 4*d*d/r) / v
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		plot.scatter(x, y, z, c='k', marker='o')