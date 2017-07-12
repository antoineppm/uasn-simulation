#!/usr/bin/env python

from math import sqrt, pi, cos, sin
from random import uniform, gauss
import numpy as np
import uncertainties.umath as um
import uncertainties.unumpy as unp
import matplotlib.pyplot as plt

def threeLaterate(Ak, K):
	"""Does the TDOA calculation based on anchor positions and range differences
	Ak          -- np.array 3x2: coordinates X,Y of the three anchors (w/out error)
	K           -- np.array 1x2: range dfference between anchor 0 and anchor 1/2 (w/ error)
	Returns an array ?x2: 0, 1 or 2 estimated position (w/error)
	"""
	# solving linear equations
	M = 2 * (Ak[0] - np.stack((Ak[1], Ak[2])))
	I = -2 * K
	J = K*K + Ak[0].dot(Ak[0]) - np.array([ Ak[1].dot(Ak[1]), Ak[2].dot(Ak[2]) ])
	A = np.linalg.inv(M).dot(I)
	B = np.linalg.inv(M).dot(J)
	# solving quadratic equation
	alpha = A.dot(A) - 1
	beta = 2*A.dot(B) - 2*A.dot(Ak[0])
	gamma = B.dot(B) - 2*B.dot(Ak[0]) + Ak[0].dot(Ak[0])
	delta = beta*beta - 4*alpha*gamma
	if delta < 0 or alpha == 0:
		return []
	elif delta == 0:
		w = -beta / (2*alpha)
		return [A*w + B]
	else:
		w1 = (-beta - um.sqrt(delta)) / (2*alpha)
		w2 = (-beta + um.sqrt(delta)) / (2*alpha)
		if w2 < 0:
			return [A*w1 + B]
		elif w1 < 0:
			return [A*w2 + B]
		else:
			return [A*w1 + B, A*w2 + B]

def generateData(Ak, x, y, N=10, sigma=0.05):
	"""Generates a set of data (range differences) for a particular point
	Ak          -- np.array 3x2: coordinates X,Y of the three anchors
	x           -- X coordinate of the point
	y           -- Y coordinate of the point
	N           -- number of data points to create
	sigma       -- standard deviation of the ranging error
	Returns:
	- an array 1x2: real range differences
	- an array Nx2: series of range dfferences between anchor 0 and anchor 1/2
	"""
	data = []
	P = np.array([x,y])
	range0 = np.linalg.norm(Ak[0] - P)
	range1 = np.linalg.norm(Ak[1] - P)
	range2 = np.linalg.norm(Ak[2] - P)
	K = np.array([range0-range1, range0-range2])
	for i in xrange(N):
		r0 = range0 * gauss(1, sigma)
		r1 = range1 * gauss(1, sigma)
		r2 = range2 * gauss(1, sigma)
		data.append(np.array([r0-r1, r0-r2]))
	return K, data


Ak = np.array( [[0, 0],
                [0, 1],
                [1, 0.5]] )

xAxis = np.arange(61)/20. - 1
yAxis = np.arange(61)/20. - 1

nodes = np.swapaxes(np.meshgrid(xAxis, yAxis), 0, 2).reshape(-1, 2)     # numpy sorcery to obtain a list of 2D points on a grid

realError = []
estError1 = []
estError2 = []
estError3 = []

for x, y in nodes:
	realK, data = generateData(Ak, x, y, sigma=0.02)
	avg = sum(data) / len(data)
	stdev = np.sqrt(sum((data-avg)**2) / len(data))
	# stdev = 0.02 * np.ones(2)
	K = unp.uarray(avg, stdev)

	p = threeLaterate(Ak, K)
	# color = {0: 'k', 1:'b', 2:'r'}[len(p)]
	# plt.scatter(x, y, c=color, marker='s', lw=0)
	
	if len(p) == 1:
		ex, ey = unp.nominal_values(p)[0]
		# plt.scatter(ex, ey, c='b', marker='+')
		# plt.plot([x,ex], [y,ey], 'b:')
		
		xlist = []
		ylist = []
		d = []
		
		N = 8
		for i in xrange(N):
			a = 2 * pi * i / N
			k = unp.uarray(avg + stdev*[cos(a),sin(a)], np.zeros(2))
			pp = threeLaterate(Ak, k)
			if len(pp) == 1:
				xx, yy = unp.nominal_values(pp)[0]
				xlist.append(xx)
				ylist.append(yy)
				d.append(sqrt( (ex-xx)**2 + (ey-yy)**2 ))
		
		if len(xlist) > 0:
			realError.append(sqrt( (x-ex)**2 + (y-ey)**2 ))
			estError1.append(sum(d) / len(d))
			estError2.append(max(d))
			nx = sum(xlist) / len(xlist)
			ny = sum(ylist) / len(ylist)
			estError3.append(sqrt( (nx-ex)**2 + (ny-ey)**2 ))
			# xlist.append(xlist[0])
			# ylist.append(ylist[0])
			# plt.plot(xlist, ylist, 'k:')
		

# for ax, ay in Ak:
# 	plt.scatter(ax, ay, c=(0,0,0,0), marker='o', s=100, lw=2, edgecolors='k')

# plt.title("Estimated error areas (sigma = 0.02)")

plt.scatter(realError, estError1, c=(0,0,1,0.5), lw=0)
plt.scatter(realError, estError2, c=(1,0,0,0.5), lw=0)
plt.scatter(realError, estError3, c=(0,1,0,0.5), lw=0)

plt.show()
