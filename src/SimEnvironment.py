#!/usr/bin/env python

from heapq import heappush, heappop
from random import uniform

class SimEnvironment:
	"""Manages a set of nodes and the communications between them"""
	def __init__(size, params = {}):
		"""Initialize the simulation environment
		size    -- dimensions (dimX, dimY, dimZ) of the simulation space
		        the simulation space is defined by the following ranges:
		            0 < x < dimX
		            0 < y < dimY
		        -dimZ < z < 0
		params  -- set of parameters, overrides the default parameters (default {})
		"""
		dimX, dimY, dimZ = size
		self.maxX = dimX
		self.maxY = dimY
		self.minZ = -dimZ
		self.params = {                     # default set of parameters
		    "speedOfSound":         1500,   # speed of sound in water (m/s)
		    "transmissionRange":    200     # maximum range a signal can reach (m)
		    "transmissionSuccess":  1       # probability of a signal reaching its destination (0 to 1)
		}
		self.params.update(params)          # let user-provided parameters override default parameters
		
		self.nodes = []
		self.events = []                    # managed with heapq
	
	def addNode(node):
		"""Adds a node to the simulation environment"""
		if node.x < 0 or node.x > self.maxX or
		   node.y < 0 or node.y > self.maxY or
		   node.z < self.minZ or node.z > 0:    # if coordinates are out of bounds, random coordinates are assigned
			node.x = uniform(0, maxX)
			node.y = uniform(0, maxY)
			node.z = uniform(minZ, 0)
		
		self.nodes.append(node)
		
		
