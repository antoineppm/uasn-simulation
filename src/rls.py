#!/usr/bin/env python

from parameters import *
from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from PositionCalculator import UPSCalculator

import numpy as np
from heapq import heappush, heappop
from itertools import combinations

class RLSNode(UWNode):
	"""Node class implementing the "reactive localization scheme"""
	slotNumber = 0
	def __init__(self, id, position = (-1,-1,0), localized = False):
		"""Create a node
		id          -- unique number identifying the node and its time slot
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		name = "node-" + str(id)
		UWNode.__init__(self, name, position)
		# common attributes
		self.message = None
		self.status = "LN" if localized else "UP"
		self.slotTimer = id
		RLSNode.slotNumber = max(id+1, RLSNode.slotNumber)
		# neighbor registration
		self.neighbors = {}
		# localization
		self.listeningTimer = 0
		self.tdoaCalc = None
		self.anchorErrors = [0, 0, 0, 0]
		# "unlocalized" status
		self.bestAnchors = []
		# "localized" status
		x, y, z = position
		self.positionEstimates = [(x, y, z, 0)] if localized else []
		self.update = False
		# "anchor" status
		self.anchorLevel = None
		self.anchorMaster = None
		self.masterDelay = None
		self.beaconTime = None
		self.beaconCount = None
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		if self.status == "A" and self.beaconTime is not None:
			if self.beaconCount == UPS_NUMBER:
				self.status = "LR"
			delay = time - self.beaconTime
			self.beaconTime = None
			beacon = self.name + " beacon " + str(self.anchorLevel) + " " + str(self.beaconCount) + " " + str(delay)
			if self.update:
				x, y, z, e = self.getPosition()
				beacon += " " + str(x) + " " + str(y) + " " + str(z) + " " + str(e)
				self.update = False
			return beacon
		
		if time / RLS_TIMESLOT > self.slotTimer:
			self.slotTimer += RLSNode.slotNumber
			print str(time) + " " + self.name + " ping " + self.status
			
			if self.status == "UP" and len(self.bestAnchors) > 0:
				self.status = "UA"
				return ""
			
			if time > self.listeningTimer:
				
				if self.status == "UA":
					s, n0, n1, n2, n3 = heappop(self.bestAnchors)
					print "score:", s
					if len(self.bestAnchors) == 0:
						self.status = "UP"
					return self.name + " request " + " ".join([n0, n1, n2, n3])
				
				if self.status == "LN":
					self.status = "LR"
					x, y, z, e = self.getPosition()
					return self.name + " position " + str(x) + " " + str(y) + " " + str(z) + " " + str(e)
				
				if self.status == "A":
					# anchor is orphaned
					self.status = "LR"
		
		return ""

	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		words = message.split()
		sender = words[0]
		subject = words[1]
		data = words[2:]
		
		if subject == "position":
			x = float(data[0])
			y = float(data[1])
			z = float(data[2])
			position = np.array([x, y, z])
			error = float(data[3])
			# if node is unlocalized, attempt to find a better anchor set
			if self.status in ["UP", "UA"]:
				self.findAnchors(sender, position, error)
			# add to the list of neighbor
			self.neighbors[sender] = (position, error)
			# revert to "unlocalized-passive" if needed
			if self.status == "UA" and time/RLS_TIMESLOT > self.slotTimer - RLSNode.slotNumber/2:
				self.status = "UP"
		
		if subject == "request":
			if self.status == "LR" and self.name in data:
				i = data.index(self.name)
				master = data[i-1 % 4]
				if master not in self.neighbors:
					return ""
				self.status = "A"
				self.anchorLevel = i
				self.anchorMaster = master
				p, e = self.neighbors[master]
				d = distance(self.position, p)
				self.masterDelay = d / SND_SPEED
				if i == 0:
					self.beaconTime = time
					self.beaconCount = 1
		
		if subject == "beacon":
			level = int(data[0])
			count = int(data[1])
			delay = float(data[2])
			if len(data) > 3:
				x = float(data[3])
				y = float(data[4])
				z = float(data[5])
				e = float(data[6])
				self.neighbors[sender] = (np.array([x,y,z]), e)
			if self.status == "A":
				self.listeningTimer = time + 4 * RLS_TIMESLOT
				if sender == self.anchorMaster:
					if self.anchorLevel == 0:
						self.beaconCount += 1
						self.beaconTime = time
					else:
						self.beaconCount = count
						self.beaconTime = time - self.masterDelay - delay
			else:
				if self.status == "UA":
					self.status = "UP"
				self.listeningTimer = time + 2 * RLS_TIMESLOT
				# first beacon: new calculator
				if count == 1 and level == 0:
					self.tdoaCalc = UPSCalculator()
				elif self.tdoaCalc is None:
					return ""
				# first cycle: register anchors
				if count == 1:
					position, error = self.neighbors[sender]
					self.tdoaCalc.addAnchor(sender, position)
					self.anchorErrors[level] = error
				else:
					if len(self.tdoaCalc.anchors) < 4:
						self.tdoaCalc = None
						return ""
				# all cycles: register data
				self.tdoaCalc.addDataPoint(sender, count, (time, delay))
				# final beacon: calculate position
				if count == UPS_NUMBER and level == 3:
					msg, position = self.tdoaCalc.getPosition()
					self.tdoaCalc = None
					print self.name + " calculating: " + msg
					print position
					if msg == "ok":
						x, y, z = position
						error = 1 + max(self.anchorErrors)
						self.positionEstimates.append((x,y,z, error))
						if self.status in ["UP", "UA"]:
							self.status = "LN"
						if self.status == "LR":
							self.update = True
		
		return ""
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		color, mark = {
			"UP": ("grey",  'v'),
			"UA": ("black", 'v'),
			"LN": ("blue",  '^'),
			"LR": ("cyan",  '^'),
			"A":  ("red",   's')
		}[self.status]
		plot.scatter(x, y, z, c=color, marker=mark, lw=0)
		if len(self.positionEstimates) > 0:
			ex, ey, ez, ee = self.getPosition()
			plot.scatter(ex, ey, ez, c=color, marker='+')
			plot.scatter(ex, ey, ez, c=(0,0,0,0.2), marker='o', lw=0, s=20*ee)
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
	
	def findAnchors(self, newNode, position, error):
		l = len(self.neighbors)
		if l >= 3:
			for n1, n2, n3 in combinations(self.neighbors.keys(), 3):
				p1, e1 = self.neighbors[n1]
				p2, e2 = self.neighbors[n2]
				p3, e3 = self.neighbors[n3]
				s = self.rateAnchors([position, p1, p2, p3], [error, e1, e2, e3])
				if s > 0:
					heappush(self.bestAnchors, (-s, newNode, n1, n2, n3))
			# print self.name + " " + str(self.bestAnchors) + " " + str(score)
	
	def rateAnchors(self, positions, errors):
		# eliminate sets where nodes are too distant
		for n1 in positions:
			for n2 in positions:
				if np.linalg.norm(n1-n2) > SIM_RANGE:
					return 0
		# calculate the score
		a = positions[1] - positions[0]
		b = positions[2] - positions[0]
		c = positions[3] - positions[0]
		shapeRating = abs(np.dot(a, np.cross(b, c)))
		errorRating = 1 + sum(errors)
		return shapeRating / errorRating
	
	def getPosition(self):
		# takes the estimate with the lowest error
		sx = 0
		sy = 0
		sz = 0
		se = float('inf')
		for x, y, z, e in self.positionEstimates:
			if e < se:
				sx = x
				sy = y
				sz = z
				se = e
		return sx, sy, sz, se
	