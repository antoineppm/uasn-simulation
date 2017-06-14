#!/usr/bin/env python

from math import sqrt
import numpy as np

class TDOACalculator:
	"""Utility class for calculating (4-laterating) positions from TDoA information"""
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
	
	def addDataPoint(self, id, anchor, toa, delay):
		"""Adds time data received from an anchor
		id          -- identifier for the measurement series
		anchor      -- anchor which sent the message (0 to 3)
		toa         -- time of reception of the message (s) (local clock)
		delay       -- time of transmission of the message (s) (anchor clock)
		"""
		if id not in self.dataArchive.keys():
			self.dataArchive[id] = [None, None, None, None]
		self.dataArchive[id][anchor] = (toa, delay)
	
	def calculatePosition(self, velocity):
		"""Calculates a position from the stored data
		velocity    -- speed of transmission of the messages (m/s)
		Returns a string ("ok" or error message) and three floats (calculated X,Y,Z coordinates if successful, 0 otherwise)
		"""
		# extracts the anchor positions
		for anchor in self.anchorPositions:
			if anchor is None:
				return ("missing anchors", 0, 0, 0)
		x0, y0, z0 = self.anchorPositions[0]
		x1, y1, z1 = self.anchorPositions[1]
		x2, y2, z2 = self.anchorPositions[2]
		x3, y3, z3 = self.anchorPositions[3]
		# k coefficients
		k1List = []
		k2List = []
		k3List = []
		for beacon in self.dataArchive.values():
			if beacon[0] is None:
				continue
			t0, dt0 = beacon[0]
			if beacon[1] is not None:
				t1, dt1 = beacon[1]
				k1List.append(t0 - dt0 - t1 + dt1)
			if beacon[2] is not None:
				t2, dt2 = beacon[2]
				k2List.append(t0 - dt0 - t2 + dt2)
			if beacon[3] is not None:
				t3, dt3 = beacon[3]
				k3List.append(t0 - dt0 - t3 + dt3)
		if len(k1List) == 0 or len(k2List) == 0 or len(k3List) == 0:
			return ("not enough data", 0, 0, 0)
		k1 = velocity * sum(k1List) / len(k1List)
		k2 = velocity * sum(k2List) / len(k2List)
		k3 = velocity * sum(k3List) / len(k3List)
		# solving linear equations
		M = np.array([ [x0-x1,  y0-y1,  z0-z1],
		               [x0-x2,  y0-y2,  z0-z2],
		               [x0-x3,  y0-y3,  z0-z3] ])
		A = np.array([ -k1,
		               -k2,
		               -k3 ])
		B = np.array([ (k1*k1 + x0*x0 + y0*y0 + z0*z0 - x1*x1 - y1*y1 - z1*z1) / 2,
		               (k2*k2 + x0*x0 + y0*y0 + z0*z0 - x2*x2 - y2*y2 - z2*z2) / 2,
		               (k3*k3 + x0*x0 + y0*y0 + z0*z0 - x3*x3 - y3*y3 - z3*z3) / 2 ])
		Ax, Ay, Az = np.linalg.solve(M, A)
		Bx, By, Bz = np.linalg.solve(M, B)
		# solving quadtratic equation
		alpha = Ax*Ax + Ay*Ay + Az*Az - 1
		beta = 2 * (Ax*Bx + Ay*By + Az*Bz - x0*Ax - y0*Ay - z0*Az)
		gamma = Bx*Bx + By*By + Bz*Bz - 2 * (x0*Bx + y0*By + z0*Bz) + x0*x0 + y0*y0 + z0*z0
		delta = beta*beta - 4*alpha*gamma
		w = 0
		if delta < 0:
			return ("no solution", 0, 0, 0)
		elif delta == 0:
			w = -beta / (2*alpha)
		else:
			w1 = (-beta - sqrt(delta)) / (2*alpha)
			w2 = (-beta + sqrt(delta)) / (2*alpha)
			if w2 < 0:
				w = w1
			elif w1 < 0:
				w = w2
			else:
				return ("two solutions", 0, 0, 0)
		# calculating the coordinates
		x = Ax*w + Bx
		y = Ay*w + By
		z = Az*w + Bz
		return ("ok", x,y,z)

# test script
calc = TDOACalculator()

# test data
calc.addAnchor(0, 0, 0, 0)
calc.addAnchor(1, 0, 500, 0)
calc.addAnchor(2, 500, 250, 0)
calc.addAnchor(3, 500, 250, -200)

calc.addDataPoint(0, 0, 1.345, 0)
calc.addDataPoint(0, 1, 1.745, 0.4)
calc.addDataPoint(0, 2, 2.080, 0.8)
calc.addDataPoint(0, 3, 2.280, 1.0)

# calculation
print calc.calculatePosition(1500)