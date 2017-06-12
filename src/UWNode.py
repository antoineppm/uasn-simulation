#!/usr/bin/env python

class UWNode:
	"""Generic class representing a node (sensor, buoy, etc...)"""
	def __init__(name, position = (-1,-1,0)):
		"""Create a node
		name        -- string identifying the node
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		self.name = name
		self.position = position
	
	def tick(time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		return ""
	
	def receive(time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
	