#!/usr/bin/env python

from parameters import *

from heapq import heappush, heappop
from random import uniform, gauss
from math import sqrt
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class SimEnvironment:
	"""Manages a set of nodes and the communications between them"""
	def __init__(self, size):
		"""Initialize the simulation environment
		size        -- dimensions (dimX, dimY, dimZ) of the simulation space
		            the simulation space is defined by the following ranges:
		                0 < x < dimX
		                0 < y < dimY
		            -dimZ < z < 0
		"""
		dimX, dimY, dimZ = size
		self.maxX = dimX
		self.maxY = dimY
		self.minZ = -dimZ
		
		self.speedMatrix = SIM_TICK * SND_VAR * np.random.randn(2,2,2)        # create a 2x2x2 array of normal (1,s) random values
		
		self.nodes = []
		self.events = []                # managed with heapq
		                                # events have the form (time, message, recipient)
		                                # if the message is empty then the function tick(time) is called for all nodes
		                                # otherwise the function receive(time, message) is called for the recipient
	
	def addNode(self, node):
		"""Adds a node to the simulation environment
		node        -- node to be added
		"""
		x, y, z = node.position
		if x < 0 or x > self.maxX or y < 0 or y > self.maxY or z < self.minZ or z > 0:  # if coordinates are out of bounds, random coordinates are assigned
			x = uniform(0, self.maxX)
			y = uniform(0, self.maxY)
			z = uniform(self.minZ, 0)
			node.position = (x,y,z)
		
		self.nodes.append(node)
	
	def run(self, timeout, verbose = False, show = 0):
		"""Runs the simulation
		timeout     -- duration of the simulation (s)
		verbose     -- output messages sent and received during the simulation
		show        -- duration between showing snapshots of the simulation (set to 0 to disable)
		"""
		heappush(self.events, (0, "", None))    # initialize the event list with a tick
		time = 0
		showTime = 0
		if verbose:
			print "start..."
		while time <= timeout:
			time, message, recipient = heappop(self.events)
			if show > 0 and time >= showTime:
				print " showing t = " + str(time)
				self.show()
				showTime += show
			if len(message) == 0:               # tick
				tick = SIM_TICK
				for node in self.nodes:
					transmission = node.tick(time)
					if len(transmission) > 0:
						self.broadcast(time, node.position, transmission)
						if verbose:
							print "%.3f" % time + " >> " + transmission
				heappush(self.events, (time + tick, "", None))
				# update the speed of sound
				N = 10                  # determines the variation speed
				self.speedMatrix *= (N - tick)
				self.speedMatrix += tick * SND_VAR * np.random.randn(2,2,2)
				self.speedMatrix /= N
			else:
				if verbose:
					print "%.3f" % time + "    " + message + " >> " + recipient.name
				recipient.receive(time, message)
		if verbose:
			print "...end"
	
	def speedOfSound(self, position):
		x, y, z = position
		v = self.speedMatrix + np.ones((2,2,2))
		# we average the matrix along each axis
		v = np.average(v, axis=0, weights=(x, self.maxX-x))
		v = np.average(v, axis=0, weights=(y, self.maxY-y))
		v = np.average(v, axis=0, weights=(z, self.minZ-z))
		return v * SND_SPEED
	
	def broadcast(self, time, position, message):
		"""Schedules a message to be recieved by all nodes in range
		time        -- date of transmission (s)
		position    -- position of broadcasting node (m,m,m)
		message     -- message to be broadcast
		"""
		for node in self.nodes:
			d = distance(node.position, position)
			if d > 0 and d <= SIM_RANGE and uniform(0,1) > SIM_LOSS:
				toa = time + d / self.speedOfSound(node.position)
				heappush(self.events, (toa, message, node))
	
	def show(self):
		"""Displays a 3D plot of the nodes"""
		# create the plot
		fig = plt.figure()
		ax = fig.add_subplot(111, projection='3d')
		# display the nodes
		for node in self.nodes:
			node.display(ax)
		# add invisible points to give the plot the right size
		maxDim = max(self.maxX, self.maxY, -self.minZ)
		ax.scatter(         [(self.maxX - maxDim)/2, (self.maxX + maxDim)/2],
		                    [(self.maxY - maxDim)/2, (self.maxY + maxDim)/2],
		                    [(self.minZ - maxDim)/2, (self.minZ + maxDim)/2],
		                    marker = '.', alpha=0)
		X, Y = np.meshgrid([0, self.maxX], [0, self.maxY])
		Z1 = np.zeros((2,2))
		Z2 = self.minZ * np.ones((2,2))
		ax.plot_surface(X, Y, Z1, color=(0,0.5,1,0.1), lw=0)
		ax.plot_surface(X, Y, Z2, color=(0,0,0,0.1), lw=0)
		ax.set_aspect('equal')
		ax.autoscale(tight=True)
		# display the plot
		mng = plt.get_current_fig_manager()
		mng.resize(*mng.window.maxsize())
		plt.show()
	
def distance(position1, position2):
	"""Calculates an euclidian distance
	position1   -- X,Y,Z coordinates of the first point (m,m,m)
	position2   -- X,Y,Z coordinates of the second point (m,m,m)
	Returns the distance between two points
	"""
	x1,y1,z1 = position1
	x2,y2,z2 = position2
	dx = x1-x2
	dy = y1-y2
	dz = z1-z2
	return sqrt(dx*dx + dy*dy + dz*dz)
		
