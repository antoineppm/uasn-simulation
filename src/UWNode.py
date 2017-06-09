#!/usr/bin/env python

class UWNode:
	"""Generic class representing a node (sensor, buoy, etc...)"""
	def __init__(name, x = -1, y = -1, z = 0):
		"""Create a node
		name    -- string identifying the node
		x       -- X coordinate of the node (default -1)
		y       -- Y coordinate of the node (default -1)
		z       -- Z coordinate of the node (default 0)
		        the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		self.name = name
		self.x = x
		self.y = y
		self.z = z
	