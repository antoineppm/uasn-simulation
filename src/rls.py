#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from TDOACalculator import TDOACalculator

class RLSNode(UWNode):
	"""Node class implementing the "reactive localization scheme"""
	params = {
		# TODO
	}
	def __init__(self, name, position = (-1,-1,0), localized = False):
		"""Create a node
		name        -- string identifying the node
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		UWNode.__init__(self, name, position)
		self.status = "LOCALIZED" if localized else "UNLOCALIZED"
		# common attributes
		self.timer = self.getTimer() if localized else float('inf')
		self.neighbors = []
		self.locData = {}
		# "LOCALIZED" attributes
		self.positionEstimate = position if localized else None
		self.errorEstimate = 0 if localized else None
		# "ANCHOR" attributes
		self.anchorId = None
		self.anchorLevel = None
		self.anchorMaster = None
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		# TODO
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		# TODO
	
	def getTimer(self):
		"""Generate a wait time, depending on current status:
		- UNLOCALIZED: random timer before request message
		- LOCALIZED: random timer before position message
		- ANCHOR: flat timer before timeout
		"""
		# TODO
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		# TODO