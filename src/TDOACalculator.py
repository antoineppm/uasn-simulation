#!/usr/bin/env python

from math import sqrt
import numpy as np
import uncertainties.umath as um
import uncertainties.unumpy as unp

from SimEnvironment import distance

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
	
	def fourLaterate(self, k1, k2, k3):
		"""Does the core calculation from the anchor positions and the delay coefficients
		k1          -- coefficient measuring the delay between anchor 0 and anchor 1
		k2          -- coefficient measuring the delay between anchor 0 and anchor 2
		k3          -- coefficient measuring the delay between anchor 0 and anchor 3
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
	
	def fourLaterateWithError(self, K):
		"""Does the core calculation from the anchor positions and the delay coefficients, including error calculations
		K           - array of coefficients measuring the delays between anchor 0 and anchor 1, 2 and 3, including the uncertainty
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates and error if successful, 0 otherwise)
		"""
		# extract the anchor positions
		for anchor in self.anchorPositions:
			if anchor is None:
				return ("missing anchors", 0, 0, 0, 0)
		P = [ np.array([x, y, z]) for x, y, z in self.anchorPositions ]
		# solving linear equations
		M = 2 * (P[0] - np.stack((P[1], P[2], P[3])))
		I = -2 * K
		J = K*K + P[0].dot(P[0]) - np.array([ P[i].dot(P[i]) for i in xrange(1,4) ])
		A = np.linalg.inv(M).dot(I)
		B = np.linalg.inv(M).dot(J)
		# solving quadratic equation
		alpha = A.dot(A) - 1
		beta = 2*A.dot(B) - 2*A.dot(P[0])
		gamma = B.dot(B) - 2*B.dot(P[0]) + P[0].dot(P[0])
		delta = beta*beta - 4*alpha*gamma
		w = 0
		if delta < 0:
			return ("no solution", 0, 0, 0, 0)
		elif delta == 0:
			w = -beta / (2*alpha)
		else:
			w1 = (-beta - um.sqrt(delta)) / (2*alpha)
			w2 = (-beta + um.sqrt(delta)) / (2*alpha)
			if w2 < 0:
				w = w1
			elif w1 < 0:
				w = w2
			else:
				return ("two solutions", 0, 0, 0, 0)
		# calculating the coordinates
		P = A*w + B
		x, y, z = unp.nominal_values(P)
		e = np.linalg.norm(unp.std_devs(P))
		return ("ok", x, y, z, e)
	
	def calculatePosition(self, velocity):
		"""Calculates a position from the stored data
		velocity    -- speed of transmission of the messages (m/s)
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates plus error estimate if successful, 0 otherwise)
		"""
		# statistical measurements and k coefficients
		kList = [ [], [], [] ]
		for beacon in self.dataArchive.values():
			if beacon[0] is None:
				continue
			t0, dt0 = beacon[0]
			if beacon[1] is not None:
				t1, dt1 = beacon[1]
				kList[0].append(t0 - dt0 - t1 + dt1)
			if beacon[2] is not None:
				t2, dt2 = beacon[2]
				kList[1].append(t0 - dt0 - t2 + dt2)
			if beacon[3] is not None:
				t3, dt3 = beacon[3]
				kList[2].append(t0 - dt0 - t3 + dt3)
		average = [0, 0, 0]
		stdev = [0, 0, 0]
		for i in xrange(3):
			kl = kList[i]
			length = len(kl)
			if length == 0:
				return ("not enough data", 0, 0, 0, 0)
			average[i] = sum(kl) / length
			stdev[i] = sqrt(sum([ (x - average[i])**2 for x in kl ]) / length)
		error = velocity * sqrt(sum([ s*s for s in stdev ]))
		k1 = velocity * average[0]
		k2 = velocity * average[1]
		k3 = velocity * average[2]
		msg, x, y, z = self.fourLaterate(k1, k2, k3)
		if msg == "ok":
			return ("ok", x, y, z, error)
		else:
			return (msg, 0, 0, 0, 0)
	
	def calculatePositionVerbose(self, velocity):
		"""Calculates a position from the stored data
		velocity    -- speed of transmission of the messages (m/s)
		Returns a string ("ok" or error message) and four floats (calculated X,Y,Z coordinates plus error estimate if successful, 0 otherwise)
		"""
		## data to return
		fullK = [ [], [], [] ]
		cleanK = [ [], [], [] ]
		
		for beacon in self.dataArchive.values():
			k1 = None
			k2 = None
			k3 = None
			
			if beacon[0] is None:
				continue
			t0, dt0 = beacon[0]
			
			if beacon[1] is not None:
				t1, dt1 = beacon[1]
				k1 = (t0 - dt0 - t1 + dt1)
				fullK[0].append(k1)
			if beacon[2] is not None:
				t2, dt2 = beacon[2]
				k2 = (t0 - dt0 - t2 + dt2)
				fullK[1].append(k2)
			if beacon[3] is not None:
				t3, dt3 = beacon[3]
				k3 = (t0 - dt0 - t3 + dt3)
				fullK[2].append(k3)
			
			if k1 is not None and k2 is not None and k3 is not None:
				cleanK[0].append(k1)
				cleanK[1].append(k2)
				cleanK[2].append(k3)
		
		## make K-average calculations on full K set
		avg = np.zeros(3)
		stdev = np.zeros(3)
		for i in xrange(3):
			kl = fullK[i]
			l = len(kl)
			if l == 0:
				return None
			avg[i] = sum(kl) / l
			stdev[i] = sqrt(sum([ (k-avg[i])**2 for k in kl ]) / l)
		K = velocity * unp.uarray(avg, stdev)
		msg, x, y, z, e = self.fourLaterateWithError(K)
		
		fullKavg = avg
		fullKsdv = stdev
		fullKpos = (x, y, z)
		fullKerr = e
		fullKresult = (fullKavg, fullKsdv, fullKpos, fullKerr)
		
		## make K-average calculations on clean K set
		avg = np.zeros(3)
		stdev = np.zeros(3)
		for i in xrange(3):
			kl = cleanK[i]
			l = len(kl)
			if l == 0:
				return None
			avg[i] = sum(kl) / l
			stdev[i] = sqrt(sum([ (k-avg[i])**2 for k in kl ]) / l)
		K = velocity * unp.uarray(avg, stdev)
		msg, x, y, z, e = self.fourLaterateWithError(K)
		
		if msg != "ok":
			return None
		
		cleanKavg = avg
		cleanKsdv = stdev
		cleanKpos = (x, y, z)
		cleanKerr = e
		cleanKresult = (cleanKavg, cleanKsdv, cleanKpos, cleanKerr)
		
		## make P-average calculations on clean K set
		xList = []
		yList = []
		zList = []
		n = 0
		
		for i in xrange(len(cleanK[0])):
			K = velocity * np.array([ kl[i] for kl in cleanK ])
			msg, x, y, z, e = self.fourLaterateWithError(K)
			if e > 1e-8:
				print e
			if msg == "ok":
				xList.append(x)
				yList.append(y)
				zList.append(z)
				n += 1
		
		if n == 0:
			return None
		
		cleanPset = [ (xList[i], yList[i], zList[i]) for i in xrange(n) ]
		cleanPpos = (sum(xList)/n, sum(yList)/n, sum(zList)/n)
		cleanPerr = sqrt(sum([ distance(p, cleanPpos) for p in cleanPset ]))
		cleanPresult = (cleanPset, cleanPpos, cleanPerr)
		
		return { "full-k-set":          fullK,
		         "full-k-average":      fullKavg,
		         "full-k-stdev":        fullKsdv,
		         "full-k-position":     fullKpos,
		         "full-k-error":        fullKerr,
		         "clean-k-set":         cleanK,
		         "clean-k-average":     cleanKavg,
		         "clean-k-stdev":       cleanKsdv,
		         "clean-k-position":    cleanKpos,
		         "clean-k-error":       cleanKerr,
		         "clean-p-set":         cleanPset,
		         "clean-p-position":    cleanPpos,
		         "clean-p-error":       cleanPerr }

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