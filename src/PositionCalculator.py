#!/usr/bin/env python

from math import sqrt
import numpy as np

from parameters import *

class PositionCalculator:
	"""Generic class handling the data-gathering side of the position calculation
	The calculation itself, specific to the method used, is left to child classes
	"""
	def __init__(self, anchorMin=1, anchorMax=-1):
		"""Creates a new calculator with empty data set
		anchorMin  -- minimum number of anchors required for the calculation
		anchorMax  -- maximum number of anchors, set to -1 if unlimited
		"""
		self.anchorMin = anchorMin
		self.anchorMax = anchorMax
		self.anchors = []       # list of anchor names
		self.positions = {}     # associates to each anchor its position (array of three numbers)
		self.data = []          # list of data series, each associating to each anchor a data point
	
	def addAnchor(self, name, position):
		"""Adds an anchor to the data set
		name        -- value identifying the anchor
		position    -- X,Y,Z coordinates of the anchor
		"""
		if len(self.anchors) == self.anchorMax:     # does nothing if the max number of anchors has been reached
			return
		
		if name not in self.anchors:
			self.anchors.append(name)
		self.positions[name] = np.array(position)
	
	def addDataPoint(self, anchor, n, data):
		"""Adds data to the data set
		anchor      -- name of the anchor from which the data comes (the anchor must have already been added)
		n           -- integer identifying the data series
		data        -- new data point (iterable of numbers with consistent length)
		"""
		# extend the data set if needed
		while len(self.data) <= n:
			self.data.append({})
		# add the data point, converted to a numpy array for ease of manipulation
		self.data[n][anchor] = np.array(data)
	
	def getPosition(self, completeOnly=False):
		"""Compiles the data stored and calculates a position estimate
		completeOnly    -- only consider complete data series
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		if len(self.anchors) < self.anchorMin:
			return "not enough anchors", np.zeros(3)
		
		if len(self.data) == 0:
			return "no data", np.zeros(3)
		
		N = len(self.compile(self.data[0])) # get the length of a compiled data series
		
		compiledData = [ [] for i in xrange(N) ]
		
		# unpack and compile each series
		for series in self.data:
			comp = self.compile(series)
			if None in comp and completeOnly:
				continue
			else:
				for i in xrange(N):
					if comp[i] is not None:
						compiledData.append(comp[i])
		
		if 0 in [ len(l) for l in compiledData ]:
			return "incomplete data", np.zeros(3)
		
		# average the compiled data
		compiledData = [ sum(l) / len(l) for l in compiledData ]
		
		# make the calculation
		return self.calculate(compiledData)
	
	def compile(self, dataSeries):
		"""Compiles a data series into a form usable by the calculation function
		Must be implemented by the child classes
		dataSeries  -- dictionary {anchor: data point}
		Returns an array of either numbers, or None when a value cannot be calculated
		"""
		return []
	
	def calculate(self, input):
		"""Calculates a position estimate from compiled data
		Must be implemented by the child classes
		input       -- compiled data
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		return "not implemented", np.zeros(3)
	
	