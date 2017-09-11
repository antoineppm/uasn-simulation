#!/usr/bin/env python

from parameters import *
from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from PositionCalculator import TDOACalculator, TOACalculator

import numpy as np
from heapq import heappush, heappop
from itertools import combinations

class RLSNode(UWNode):
	"""Node class implementing the "reactive localization scheme"""
	
	slotNumber = 0  # number of time slots in a full cycle
	
	def __init__(self, id, position = (-1,-1,0), localized = False):
		"""Create a node
		id          -- unique number identifying the node and its time slot
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		name = "node-" + str(id)
		UWNode.__init__(self, name, position)
		# common attributes
		self.status = ["ANCHOR", "init"] if localized else ["UNLOCALIZED", "idle"]  # primary and secondary status of the node
		self.timestamp = 0              # multipurpose time stamp, meaning depends on current state (unit: s)
		                                # UNLOCALIZED: silence after certain messages
		                                # /confirming, ANCHOR/active: timeout
		                                # LOCALIZED/toa: time origin
		self.slotTimer = id             # timer indicating the next timeslot (unit: timeslot length)
		RLSNode.slotNumber = max(id+1, RLSNode.slotNumber)
		# neighbor registration
		self.neighbors = {}             # associates a pair bool,position to each neighbor's name
		                                # the boolean indicates if the neighbor is an anchor (precisely located)
		# localization
		self.calculator = None          # can be either TDOA or TOA calculator
		# "unlocalized" status
		self.bestAnchors = []
		# "localized" status
		self.positionEstimates = [np.array(position)] if localized else []
		# "anchor" status
		self.subAnchors = []            # anchors coming after in the beaconing cycle that have not anchor rank yet
		self.anchorLevel = 0            # place in the beaconing
		self.anchorMaster = None        # anchor coming just before in the beaconing cycle
		self.beaconCount = 1            # counts the beaconing series
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		
		if time / RLS_TIMESLOT > self.slotTimer:
			self.slotTimer += RLSNode.slotNumber
			timeslotOpen = True
			# print self.name, self.status[0] + "/" + self.status[1]
		else:
			timeslotOpen = False
		
		if self.status[0] == "UNLOCALIZED":
			if self.status[1] == "idle":
				if timeslotOpen and len(self.bestAnchors) > 0:
					self.status[1] = "requesting"
					self.timestamp = time + 2*RLS_TIMESLOT
			
			elif self.status[1] == "requesting":
				if timeslotOpen and time > self.timestamp:
					self.status[1] = "idle"
					s, n0, n1, n2, n3 = heappop(self.bestAnchors)
					return self.name + " request " + " ".join([n0, n1, n2, n3])
		
		elif self.status[0] == "LOCALIZED":
			if self.status[1] == "new":
				if timeslotOpen and time > self.timestamp:
					self.status[1] = "ready"
					x, y, z = self.getPosition()
					return self.name + " position " + str(x) + " " + str(y) + " " + str(z)
			
			elif self.status[1] == "confirming":
				if time > self.timestamp:
					print self.name, self.status, "timeout", self.timestamp
					self.status[1] = "ready"
			
			elif self.status[1] == "toa":
				if time > self.timestamp + 2*RLS_TIMESLOT:
					msg, position = self.calculator.getPosition()
					if msg == "ok":
						print self.name, msg, position, distance(position, self.position)
						self.status = ["ANCHOR", "confirming"]
						self.timestamp = time + RLS_TIMESLOT
						self.positionEstimates = [position]
						x, y, z = position
						return self.name + " anchor " + " " + str(x) + " " + str(y) + " " + str(z)
					else:
						self.status[1] = "ready"
		
		elif self.status[0] == "ANCHOR":
			if self.status[1] == "confirming":
				if time > self.timestamp:
					print self.name, self.status, "timeout", self.timestamp
					self.status[1] = "ready"
			
			elif self.status[1] == "active":
				if time > self.timestamp:
					print self.name, self.status, "timeout", self.timestamp
					self.status[1] = "ready"
			
			elif self.status[1] == "init":
				if timeslotOpen:
					self.status[1] = "ready"
					x, y, z = self.getPosition()
					return self.name + " anchor " + str(x) + " " + str(y) + " " + str(z)
		
		if self.status[1] == "confirming":
			# similar behavior regardless of primary status
			if len(self.subAnchors) == 0:
				if self.status[0] == "ANCHOR":
					self.status[1] = "active"
					if self.anchorLevel == 0:
						return self.name + " beacon 0 1 0"
				else:
					self.status[1] = "toa"
					self.calculator = TOACalculator(self.getPosition())
					self.timestamp = time
					return self.name + " ping"
			elif time > self.timestamp:
				print self.name, self.status, "timeout", self.timestamp
				self.status[1] = "ready"
			
		
		return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		words = message.split()
		sender = words[0]
		subject = words[1]
		data = words[2:]
		
		if subject == "position":
			# ALL: register the neighbor
			# UNLOCALIZED: find new anchor sets
			x = float(data[0])
			y = float(data[1])
			z = float(data[2])
			position = np.array([x, y, z])
			# add to the list of neighbor
			self.neighbors[sender] = (False, position)
			# if node is unlocalized, attempt to find a better anchor set, and revert to "idle" status
			if self.status[0] == "UNLOCALIZED":
				self.findAnchors(sender, position)
				self.status[1] = "idle"
		
		if subject == "anchor":
			# ALL: register the neighbor
			# UNLOCALIZED: update anchor ratings
			# confirming: remove from the list of sub-anchors, if applicable
			x = float(data[0])
			y = float(data[1])
			z = float(data[2])
			position = np.array([x, y, z])
			# add to the list of neighbor
			self.neighbors[sender] = (True, position)
			# if node is unlocalized, attempt to find a better anchor set, and revert to "idle" status
			if self.status[0] == "UNLOCALIZED":
				self.findAnchors(sender, position)
				self.status[1] = "idle"
			# remove from sub-anchors
			while sender in self.subAnchors:
				self.subAnchors.remove(sender)
		
		if subject == "request":
			# silence timer
			if self.status[0] == "UNLOCALIZED" or self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			# /ready, concerned: transition to /confirming
			# if level 0: transition to next state
			if self.status[1] == "ready" and self.name in data:
				for node in data:
					if node not in self.neighbors and node != self.name:
						return ""
				i = data.index(self.name)
				self.subAnchors =  [ node for node in data[i+1:] if not self.neighbors[node][0] ]
				self.anchorLevel = i
				self.anchorMaster = data[(i-1) % 4]
				self.status[1] = "confirming"
				self.timestamp = time + RLS_TIMESLOT
				self.beaconCount = 1
		
		if subject == "ping":
			# silence & timeout
			if self.status[0] == "UNLOCALIZED" or self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			if self.status[1] == "confirming" or self.status[1] == "active":
				self.timestamp = time + 3*RLS_TIMESLOT
			# if ANCHOR: send "ack"
			if self.status[0] == "ANCHOR":
				return self.name + " ack " + sender + " " + str(SIM_TICK)
		
		if subject == "ack":
			# silence timer
			if self.status[0] == "UNLOCALIZED" or self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			# if concerned: register TOA data
			recipient = data[0]
			delay = float(data[1])
			if self.status[1] == "toa":
				if self.name == recipient:
					self.calculator.addAnchor(sender, self.neighbors[sender][1])
					self.calculator.addDataPoint(sender, 0, (time - self.timestamp, delay))
		
		if subject == "beacon":
			# silence & timeout
			if self.status[0] == "UNLOCALIZED":
				self.status[1] = "idle"
			if self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			if self.status[1] == "active":
				self.timestamp = time + RLS_TIMESLOT
			# not ANCHOR: register TDOA data
			# ANCHOR/active, concerned: send "beacon"
			level = int(data[0])
			count = int(data[1])
			delay = float(data[2])
			if self.status == ["ANCHOR", "active"]:
				# check if concerned
				if sender != self.anchorMaster:
					return ""
				if (level+1)%4 != self.anchorLevel:
					# should not happen!
					self.status[1] = "ready"
					return ""
				if self.anchorLevel == 0:
					self.beaconCount += 1
					newDelay = 0
				else:
					self.beaconCount = count
					timeToMaster = distance(self.getPosition(), self.neighbors[sender][1]) / SND_SPEED
					newDelay = delay + timeToMaster + SIM_TICK
				if self.beaconCount == UPS_NUMBER:
					self.status[1] = "ready"
				return self.name + " beacon " + str(self.anchorLevel) + " " + str(self.beaconCount) + " " + str(newDelay)
			elif self.status[0] != "ANCHOR":
				if count == 1 and level == 0:
					self.calculator = TDOACalculator()
				elif self.calculator is None:
					return ""
				if count == 1 and len(self.calculator.anchors) == level and sender not in self.calculator.anchors:
					self.calculator.addAnchor(sender, self.neighbors[sender][1])
				elif len(self.calculator.anchors) < 4:
					self.calculator = None
					return ""
				if sender != self.calculator.anchors[level]:
					return ""
				# register data
				self.calculator.addDataPoint(sender, count, (time, delay))
				# if finished, do calculation
				if level == 3 and count == UPS_NUMBER:
					msg, position = self.calculator.getPosition()
					print self.name, msg, position, distance(position, self.position)
					if msg == "ok":
						self.positionEstimates.append(position)
						if self.status[0] == "UNLOCALIZED":
							self.status = ["LOCALIZED", "new"]
					self.calculator = None
		
		return ""
					
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		color, mark = {
			"UNLOCALIZED": ("grey",  'v'),
			"LOCALIZED": ("black", '^'),
			"ANCHOR": ("blue",  '^')
		}[self.status[0]]
		plot.scatter(x, y, z, c=color, marker=mark, lw=0)
		if len(self.positionEstimates) > 0:
			ex, ey, ez = self.getPosition()
			plot.scatter(ex, ey, ez, c=color, marker='+')
			# plot.scatter(ex, ey, ez, c=(0,0,0,0.2), marker='o', lw=0, s=20*ee)
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
	
	def findAnchors(self, newNode, position):
		# very inefficient function
		self.bestAnchors = []
		l = len(self.neighbors)
		if l >= 4:
			for n0, n1, n2, n3 in combinations(self.neighbors.keys(), 4):
				s = self.rateAnchors([n0, n1, n2, n3])
				if s > 0:
					heappush(self.bestAnchors, (-s, n0, n1, n2, n3))
	
	def rateAnchors(self, anchors):
		isAnchor = [ self.neighbors[node][0] for node in anchors ]
		positions = [ self.neighbors[node][1] for node in anchors ]
		# eliminate sets where nodes are too distant
		avgDist = 0
		for n1 in positions:
			for n2 in positions:
				d = np.linalg.norm(n1-n2)
				if d > SIM_RANGE:
					return 0
				else:
					avgDist += d
		avgDist /= 12
		# calculate the score
		sizeRating = min(avgDist, SIM_RANGE/2)
		a = positions[1] - positions[0]
		b = positions[2] - positions[0]
		c = positions[3] - positions[0]
		shapeRating = abs(np.dot(a, np.cross(b, c)))**(1/3) / avgDist
		anchorRating = (1 + sum(isAnchor))**2
		return sizeRating * shapeRating * anchorRating
	
	def getPosition(self):
		# average the estimates
		return sum(self.positionEstimates) / len(self.positionEstimates)
	