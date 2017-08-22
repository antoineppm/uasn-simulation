#!/usr/bin/env python

from math import sqrt
import numpy as np
import uncertainties.umath as um
import uncertainties.unumpy as unp

from SimEnvironment import distance

class TOACalculator:
	"""Utility class for calculating positions from ToA information"""
	def __init__(self):
		"""Creates an empty data set for receiving localization information"""
		self.anchorPositions = [None, None, None, None]     # contains coordinate sets (x,y,z)
		self.dataArchive = {}                               # contains data points (time of arrival and transmission delay for each anchor) associated with an identifier
	
	def addAnchor(self, anchor, x, y, z):
		"""Specify the coordinates of an anchor
		All four anchor needs to be given for the calculation to be possible
		anchor      -- number identifying the anchor (0 to 3)
		x           -- X coordinate of the anchor (m)
		y           -- Y coordinate of the anchor (m)
		z           -- Z coordinate of the anchor (m)
		"""
		self.anchorPositions[anchor] = (x,y,z)
	
	def addDataPoint(self, id, anchor, tof, delay):
		"""Adds time data received from an anchor
		id          -- identifier for the measurement series
		anchor      -- anchor which sent the message (0 to 3)
		tof         -- time of flight (round trip)
		delay       -- time between reception and reply by the anchor
		"""
		if id not in self.dataArchive.keys():
			self.dataArchive[id] = [None, None, None, None]
		self.dataArchive[id][anchor] = (tof - delay) / 2
	
	def threeLaterate(self, D):
		"""Does the core calculation from the anchor positions and the distances, including error calculations
		D           -- array of distance between the node and each anchor
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates and error if successful, 0 otherwise)
		"""
		# TO DO