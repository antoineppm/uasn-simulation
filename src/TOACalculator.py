#!/usr/bin/env python

from math import sqrt
import numpy as np
import uncertainties.umath as um
import uncertainties.unumpy as unp

from SimEnvironment import distance
from parameters import *

class TOACalculator:
	"""Utility class for calculating positions from ToA information"""
	def __init__(self):
		"""Creates an empty data set for receiving localization information"""
		self.anchors = {}
		self.dataArchive = {}                               # contains data points (time of arrival and transmission delay for each anchor) associated with an identifier
	
	def addAnchor(self, anchor, x, y, z):
		"""Specify the coordinates of an anchor
		All four anchor needs to be given for the calculation to be possible
		anchor      -- name of the anchor
		x           -- X coordinate of the anchor (m)
		y           -- Y coordinate of the anchor (m)
		z           -- Z coordinate of the anchor (m)
		"""
		self.anchors[anchor] = [x,y,z]
		if anchor not in self.dataArchive.keys():
			self.dataArchive[anchor] = []
	
	def addDataPoint(self, anchor, tof, delay):
		"""Adds time data received from an anchor
		anchor      -- name of the anchor
		tof         -- time of flight (round trip)
		delay       -- time between reception and reply by the anchor
		"""
		if anchor in self.dataArchive.keys():
			self.dataArchive[anchor].append((tof - delay) / 2)
		else:
			raise "add anchor first"
	
	def GaussNewton(self, X0, A, D):
		"""Does the core calculation from the anchor positions and the distances, including error calculations
		X0          -- prior position estimate
		A           -- array (N,3) of anchor positions
		D           -- array (N) of distance between the node and each anchor
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates and error if successful, 0 otherwise)
		"""
		X = np.array(X0)
		N = len(A)   # number of anchors
		
		for k in xrange(TOA_ITERMAX):
			R = np.zeros(N)     # residuals matrix
			J = np.zeros((N,3)) # Jacobian matrix
			
			for i in xrange(N):
				dist = np.linalg.norm(A[i] - X)
				R[i] = D[i] - dist
				J[i] = (A[i] - X) / dist
			
			diff = np.linalg.inv(J.T.dot(J)).dot(J.T).dot(R)    # differential of the Gauss-Newton method
			var = np.linalg.norm(diff)
			
			# print k
			# print X
			# print R
			# print J
			# print var
			# print diff
			
			X = X - diff
			if var < TOA_THRESHOLD:
				break
		
		# print "finished at iteration " + str(k+1) + " with variation " + str(var)
		return X
	
	def calculatePosition(self, X0=(0,0,0)):
		"""Calculate a position from the stored data
		X0          -- prior position estimate
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates and error if successful, 0 otherwise)
		"""
		A = []
		D = []
		for a in self.anchors:
			A.append(self.anchors[a])
			s = sum(self.dataArchive[a])
			l = len(self.dataArchive[a])
			D.append(s/l)
		return self.GaussNewton(X0, np.array(A), np.array(D))
			
	