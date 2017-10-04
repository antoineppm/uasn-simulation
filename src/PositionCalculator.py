#!/usr/bin/env python

from math import sqrt
import numpy as np

from parameters import *

class PositionCalculator:
	"""Generic class handling the data-gathering side of the position calculation
	The calculation itself, specific to the method used, is left to child classes
	"""
	def __init__(self):
		"""Creates a new calculator with empty data set
		"""
		self.anchors = []       # list of anchor names
		self.positions = {}     # associates to each anchor its position (array of three numbers)
		self.data = []          # list of data samples, each associating to each anchor a data point
		
		# parameters to be set by the child classes
		self.anchorMin = 1      # minimum number of anchors required for the calculation
		self.anchorMax = -1     # minimum number of anchors required for the calculation (-1 for unlimited)
	
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
		n           -- integer identifying the data sample
		data        -- new data point (iterable of numbers with consistent length)
		"""
		# extend the data set if needed
		while len(self.data) <= n:
			self.data.append({})
		# add the data point, converted to a numpy array for ease of manipulation
		self.data[n][anchor] = np.array(data)
	
	def getPosition(self, completeOnly=False):
		"""Compiles the data stored and calculates a position estimate
		completeOnly    -- only consider complete data sample
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		if len(self.anchors) < self.anchorMin:
			return "not enough anchors", np.zeros(3)
		
		if len(self.data) == 0:
			return "no data", np.zeros(3)
		
		N = len(self.compile(self.data[0])) # get the length of a compiled data sample
		
		compiledData = [ [] for i in xrange(N) ]
		
		# unpack and compile each sample
		for sample in self.data:
			comp = self.compile(sample)
			if None in comp and completeOnly:
				continue
			else:
				for i in xrange(N):
					if comp[i] is not None:
						compiledData[i].append(comp[i])
		
		if 0 in [ len(l) for l in compiledData ]:
			return "incomplete data", np.zeros(3)
		
		# average the compiled data
		compiledData = np.array([ sum(l) / len(l) for l in compiledData ])
		
		# make the calculation
		return self.calculate(compiledData)
	
	def compile(self, sample):
		"""Compiles a data sample into a form usable by the calculation function
		Must be implemented by the child classes
		sample      -- dictionary {anchor: data point}
		Returns an array of either numbers, or None when a value cannot be calculated
		"""
		return []
	
	def calculate(self, data):
		"""Calculates a position estimate from compiled data
		Must be implemented by the child classes
		data        -- compiled data
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		return "not implemented", np.zeros(3)
	

class UPSCalculator(PositionCalculator):
	"""Position calculation for the UPS process
	"""
	def __init__(self):
		"""Creates a new calculator with empty data set
		"""
		PositionCalculator.__init__(self)
		self.anchorMin = 4
		self.anchorMax = 4
	
	def compile(self, sample):
		"""Compiles a data sample into a form usable by the calculation function
		Must be implemented by the child classes
		sample      -- dictionary {anchor: data point}
		Returns an array of either numbers, or None when a value cannot be calculated
		"""
		distDiff = [ None for i in xrange(3) ]
		if self.anchors[0] in sample:
			t0, dt0 = sample[self.anchors[0]]
			for i in xrange(3):
				if self.anchors[i+1] in sample:
					t, dt = sample[self.anchors[i+1]]
					distDiff[i] = (t0 - dt0 - t + dt) * SND_SPEED
		return distDiff
	
	def calculate(self, data):
		"""Calculates a position estimate from compiled data
		Must be implemented by the child classes
		data        -- compiled data
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		K = data
		P = [ self.positions[a] for a in self.anchors ]
		# solving linear equations
		M = 2 * (P[0] - np.stack((P[1], P[2], P[3])))
		I = -2 * K
		J = K*K + P[0].dot(P[0]) - np.array([ P[i].dot(P[i]) for i in xrange(1,4) ])
		try:
			A = np.linalg.inv(M).dot(I)
			B = np.linalg.inv(M).dot(J)
		except np.linalg.linalg.LinAlgError:
			print M
			return "could not be solved", np.zeros(3)
		# solving quadratic equation
		alpha = A.dot(A) - 1
		beta = 2*A.dot(B) - 2*A.dot(P[0])
		gamma = B.dot(B) - 2*B.dot(P[0]) + P[0].dot(P[0])
		delta = beta*beta - 4*alpha*gamma
		# calculating root(s)
		if delta < 0:
			roots = []
		if delta == 0:
			roots = [ -beta / (2*alpha) ]
		if delta > 0:
			roots = [ (-beta - sqrt(delta)) / (2*alpha),
			          (-beta + sqrt(delta)) / (2*alpha) ]
		# selecting valid results
		positions = []
		for r in roots:
			# eliminate negative solutions
			if r < 0:
				continue
			# calculate the positon
			pos = A*r + B
			# check it's at a valid distance from each anchor
			if max([ np.linalg.norm(pos-a) for a in P ]) <= SIM_RANGE * 1.1:
				positions.append(pos)
		# return the result
		if len(positions) == 0:
			return "no result", np.zeros(3)
		elif len(positions) == 1:
			return "ok", positions[0]
		else:
			return "multiple results", np.zeros(3)
		

class TOACalculator(PositionCalculator):
	"""Position calculation based on the time of arrival
	"""
	def __init__(self, position):
		"""Creates a new calculator with empty data set
		position    -- prior position estimate
		"""
		PositionCalculator.__init__(self)
		self.anchorMin = 3
		self.anchorMax = -1
		self.priorPosition = np.array(position)
	
	
	def compile(self, sample):
		"""Compiles a data sample into a form usable by the calculation function
		Must be implemented by the child classes
		sample      -- dictionary {anchor: data point}
		Returns an array of either numbers, or None when a value cannot be calculated
		"""
		distances = [ None for i in xrange(len(self.anchors)) ]
		for i, a in enumerate(self.anchors):
			if a in sample:
				tof, dt = sample[a]
				distances[i] = SND_SPEED * (tof - dt) / 2
		return distances
	
	def calculate(self, data):
		"""Calculates a position estimate from compiled data, using the Gauss-Newton method
		Must be implemented by the child classes
		data        -- compiled data
		Returns an error message ("ok" if successful) and the estimated position as a numpy array
		"""
		X = self.priorPosition
		N = len(data)
		
		for k in xrange(TOA_ITERMAX):
			R = np.zeros(N)     # residuals matrix
			J = np.zeros((N,3)) # Jacobian matrix
			
			for i, a in enumerate(self.anchors):
				dist = np.linalg.norm(self.positions[a] - X)
				R[i] = data[i] - dist
				J[i] = (self.positions[a] - X) / dist
			
			try:
				diff = np.linalg.inv(J.T.dot(J)).dot(J.T).dot(R)    # differential of the Gauss-Newton method
			except np.linalg.linalg.LinAlgError:
				print k, J, J.T.dot(J)
				return "could not be solved", np.zeros(3)
			var = np.linalg.norm(diff)
			X = X - diff
			
			if var < TOA_THRESHOLD:
				return "ok", X
		
		return "reached iteration maximum", X
