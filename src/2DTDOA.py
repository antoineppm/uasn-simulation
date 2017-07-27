#!/usr/bin/env python

from math import sqrt, pi, cos, sin
from random import uniform, gauss, randrange
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

def speedOfSound(p1, p2, speedMatrix):
	"""Interpolates the speed of sound at the middle of two points
	p1          -- coordinates X,Y of the first point
	p2          -- coordinates X,Y of the second point
	speedMatrix -- speed of sound at each corner of the square (0,1)
	"""
	x, y = (p1 + p2) / 2
	v = speedMatrix
	v = np.average(v, axis=0, weights=(1-x, x))
	v = np.average(v, axis=0, weights=(1-y, y))
	return v
	

def generateData(Ak, x, y, N=10, speedMatrix=np.ones((2,2)), sigma=0.001):
	"""Generates a set of data (range differences) for a particular point
	Ak          -- np.array 3x2: coordinates X,Y of the three anchors
	x           -- X coordinate of the point
	y           -- Y coordinate of the point
	N           -- number of data points to create
	speedMatrix -- speed of sound at each corner of the square (0,1)
	sigma       -- standard deviation of the additional ranging error
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
		v0 = speedOfSound(P, Ak[0], speedMatrix)
		r0 = range0 / v0 * gauss(1, sigma)
		v1 = speedOfSound(P, Ak[1], speedMatrix)
		r1 = range1 / v1 * gauss(1, sigma)
		v2 = speedOfSound(P, Ak[2], speedMatrix)
		r2 = range2 / v2 * gauss(1, sigma)
		data.append([r0-r1, r0-r2])
	return K, np.array(data)

plot = "data"

Ak = np.array( [[0, 0],
                [0, 1],
                [1, 1]] )

if plot == "plane":
	for ax, ay in Ak:
		plt.scatter(ax, ay, c=(0,0,0,0), marker='o', s=100, lw=2, edgecolors='k')
	plt.title("")

step = 2 if plot == "plane" else 10
nb = 3 * step + 1.

xAxis = np.arange(nb)/step - 1
yAxis = xAxis

nodes = np.swapaxes(np.meshgrid(xAxis, yAxis), 0, 2).reshape(-1, 2)     # numpy sorcery to obtain a list of 2D points on a grid

xdata = [ [], [], [] ]
ydata = [ [], [], [], [], [] ]

vsigma = 0.0
speeds = 1 + vsigma * np.random.randn(2,2)

for x, y in nodes:
	pos = np.array([x, y])
	
	realK, data = generateData(Ak, x, y, speedMatrix=speeds, sigma=0.02)
	avg = sum(data) / len(data)
	stdev = np.sqrt(sum((data-avg)**2) / len(data))
	K = unp.uarray(avg, stdev)

	p = threeLaterate(Ak, K)
	if plot == "plane":
		color = {0: 'k', 1:'r', 2:'b'}[len(p)]
		plt.scatter(x, y, c=color, marker='s', lw=0)
	
	if len(p) == 1:
		epos = unp.nominal_values(p)[0]
		ex, ey = epos
		if plot == "plane":
			plt.scatter(ex, ey, c='r', marker='+')
			plt.plot([x,ex], [y,ey], 'r:')
		
		sigList = []
		d = []
		
		N = 8
		for i in xrange(N):
			a = 2 * pi * i / N
			f = 1
			k = unp.uarray(avg + stdev*[cos(a),sin(a)]*f, np.zeros(2))
			pp = threeLaterate(Ak, k)
			if len(pp) == 0:
				continue
			elif len(pp) == 1:
				xx, yy = unp.nominal_values(pp)[0]
			elif len(pp) == 2:
				d0 = np.linalg.norm(unp.nominal_values(pp)[0] - epos)
				d1 = np.linalg.norm(unp.nominal_values(pp)[1] - epos)
				xx, yy = unp.nominal_values(pp)[ 0 if d0 < d1 else 1 ]
			sigList.append([xx, yy])
			d.append(sqrt( (ex-xx)**2 + (ey-yy)**2 ))
		
		if len(sigList) == N:
			sigList = np.array(sigList)
			npos = sum(sigList) / N
			nx, ny = npos
			xlist = sigList[:,0].tolist()
			ylist = sigList[:,1].tolist()
			xlist.append(xlist[0])
			ylist.append(ylist[0])
			
			maxdim = max( [ max( [ np.linalg.norm(p1-p2) for p2 in sigList ] ) for p1 in sigList ] )
			
			area = 0
			for i in xrange(N):
				ax = xlist[i]
				ay = ylist[i]
				bx = xlist[i+1]
				by = ylist[i+1]
				area += abs( (ex*(ay-by) + ax*(by-ey) + bx*(ey-ay)) / 2 )
			
			if plot == "plane":
				plt.scatter(nx, ny, c='k', marker='+')
				plt.plot([x,nx], [y,ny], 'k:')
				plt.plot(xlist, ylist, 'k:')
				print x, y
				print ex, ey, np.linalg.norm(epos - pos)
				print maxdim, area
				print ""
			if plot == "data":
				apos = (2*epos + N*npos) / (2+N)
				for i, p in enumerate([epos, npos, apos]):
					xdata[i].append(np.linalg.norm(p - pos))
					ydata[i].append( sqrt(sum([ np.linalg.norm(p-sigp)**2 for sigp in sigList ]) / N) )
				ydata[3].append(maxdim)
				ydata[4].append(area)

validPoints = []
for i in xrange(len(xdata[0])):
	valid = True
	for yd in ydata:
		if yd[i] > 1:
			valid = False
	if valid:
		validPoints.append(i)

xdata = [ [ xd[i] for i in validPoints ] for xd in xdata ]
ydata = [ [ yd[i] for i in validPoints ] for yd in ydata ]

montecarlo = 1000000

if plot == "data":
	ydata = [ ydata[0], ydata[3], ydata[4] ]
	fig, ax = plt.subplots(len(ydata), len(xdata))
	for i, xd in enumerate(xdata):
		for j, yd in enumerate(ydata):
			ax[j,i].scatter(xd, yd, c=(i/2.,j/2.,1-i/2.,0.5), lw=0)
			# 0,0: blue
			# 0,1: cyan
			# 1,0: red
			# 1,1: yellow
			s = 0.
			for k in xrange(montecarlo):
				a = randrange(len(xd))
				b = randrange(len(xd))
				if (xd[a] > xd[b]) == (yd[a] > yd[b]):
					s += 1
			print i, j, s/montecarlo

plt.show()
