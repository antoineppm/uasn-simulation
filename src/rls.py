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
		self.neighbors = {}             # associates a position to each neighbor's name
		# localization
		self.calculator = None          # can be either TDOA or TOA calculator
		# "unlocalized" status
		self.bestAnchors = []
		# "localized" status
		self.positionEstimates = [np.array(position)] if localized else []
		# "anchor" status
		self.anchorLevel = None         # place in the beaconing order (0 to 3)
		self.anchorMaster = None        # name of the previous anchor in the beaconing order (or last one if level = 0)
		self.beaconCount = None         # counts the beaconing series
	
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
				if time > self.timestamp + 2*(SIM_TICK + SIM_RANGE/SND_SPEED):
					msg, position = self.calculator.getPosition()
					if msg == "ok":
						self.status[0] = "ANCHOR"
						self.status[1] = "confirming" if self.anchorLevel == 0 else "active"
						self.timestamp = time + RLS_TIMESLOT
						self.positionEstimates = [position]
						x, y, z = position
						return self.name + " confirm " + str(self.anchorLevel) + " " + str(x) + " " + str(y) + " " + str(z)
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
					return self.name + " position " + str(x) + " " + str(y) + " " + str(z)
		
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
			# if node is unlocalized, attempt to find a better anchor set, and revert to "idle" status
			if self.status[0] == "UNLOCALIZED":
				self.findAnchors(sender, position)
				self.status[1] = "idle"
			# add to the list of neighbor
			self.neighbors[sender] = position
		
		confirmed = False
		beaconing = False
		
		if subject == "request":
			# silence timer
			if self.status[0] == "UNLOCALIZED" or self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			# /ready, concerned: transition to /confirming
			# if level 0: transition to next state
			if self.status[1] == "ready" and self.name in data:
				i = data.index(self.name)
				master = data[i-1 % 4]
				if master not in self.neighbors:
					return ""
				self.status[1] = "confirming"
				self.timestamp = time + RLS_TIMESLOT
				self.anchorLevel = i
				self.anchorMaster = master
				self.beaconCount = 0
				if i == 0:
					confirmed = True
		
		if subject == "confirm":
			# silence & timeout
			if self.status[0] == "UNLOCALIZED" or self.status[1] == "new":
				self.timestamp = time + 2*RLS_TIMESLOT
			if self.status[1] == "confirming" or self.status[1] == "active":
				self.timestamp = time + RLS_TIMESLOT
			# ALL: register the position
			# not ANCHOR, not /confirming: prepare TDOA calculations
			# /confirming, concerned: send "confirm", transition to next state
			# if LOCALIZED: send "ping"
			# if ANCHOR, level 0: send "beacon"
			level = int(data[0])
			x = float(data[1])
			y = float(data[2])
			z = float(data[3])
			position = np.array([x, y, z])
			self.neighbors[sender] = position
			if self.status[1] == "confirming":
				if sender == self.anchorMaster:
					self.status[1] = "active"
					if self.anchorLevel == 0:
						beaconing = True
					else:
						confirmed = True
			elif self.status[0] != "ANCHOR":
				if level == 0 and self.calculator is None:
					self.calculator = TDOACalculator()
					self.calculator.addAnchor(sender, position)
				elif self.calculator is not None:
					if level == len(self.calculator.anchors):
						self.calculator.addAnchor(sender, position)
		
		if confirmed:
			if self.status[0] == "ANCHOR":
				self.timestamp = time + RLS_TIMESLOT
				x, y, z = self.getPosition()
				return self.name + " confirm " + str(self.anchorLevel) + " " + str(x) + " " + str(y) + " " + str(z)
			else:
				self.status[1] = "toa"
				self.timestamp = time + SIM_TICK
				self.calculator = TOACalculator(self.getPosition())
				return self.name + " ping"
		
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
					self.calculator.addAnchor(sender, self.neighbors[sender])
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
				beaconing = True
			else:
				# check if concerned
				if self.calculator is None:
					return ""
				if len(self.calculator.anchors) < 4:
					return ""
				if sender != self.calculator.anchors[level]:
					return ""
				# register data
				self.calculator.addDataPoint(sender, count, (time, delay))
				# if finished, do calculation
				if level == 3 and count == UPS_NUMBER:
					msg, position = self.calculator.getPosition()
					print self.name, msg, position
					if msg == "ok":
						self.positionEstimates.append(position)
						if self.status[0] == "UNLOCALIZED":
							self.status = ["LOCALIZED", "new"]
					self.calculator = None
		
		if beaconing:
			if self.anchorLevel == 0:
				self.beaconCount += 1
				newDelay = 0
			else:
				self.beaconCount = count
				timeToMaster = distance(self.getPosition(), self.neighbors[sender]) / SND_SPEED
				newDelay = delay + timeToMaster + SIM_TICK
			if self.beaconCount == UPS_NUMBER:
				self.status[1] = "ready"
			return self.name + " beacon " + str(self.anchorLevel) + " " + str(self.beaconCount) + " " + str(newDelay)
		
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
		l = len(self.neighbors)
		if l >= 3:
			for n1, n2, n3 in combinations(self.neighbors.keys(), 3):
				p1 = self.neighbors[n1]
				p2 = self.neighbors[n2]
				p3 = self.neighbors[n3]
				s = self.rateAnchors([position, p1, p2, p3])
				if s > 0:
					heappush(self.bestAnchors, (-s, newNode, n1, n2, n3))
			# print self.name + " " + str(self.bestAnchors) + " " + str(score)
	
	def rateAnchors(self, positions):
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
		return shapeRating
	
	def getPosition(self):
		# average the estimates
		return sum(self.positionEstimates) / len(self.positionEstimates)
	