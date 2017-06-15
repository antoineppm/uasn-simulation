#!/usr/bin/env python

class UWNode:
	"""Generic class representing a node (sensor, buoy, etc...)"""
	def __init__(self, name, position = (-1,-1,0)):
		"""Create a node
		name        -- string identifying the node
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		self.name = name
		self.position = position
		self.speedOfSound = 0   # to be modified by the simulation environment
	
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
	
	def representation(self):
		"""Indicates one or more points (coordinates and style) representing the node
		Returns a list of points: (x, y, z, color, marker)
		"""
		x, y, z = self.position
		return [(x, y, z, 'k', 'o')]	# a black circle at the position of the node
	