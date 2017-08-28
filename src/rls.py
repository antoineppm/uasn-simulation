#!/usr/bin/env python

from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from TDOACalculator import TDOACalculator

class RLSNode(UWNode):
	"""Node class implementing the "reactive localization scheme"""
	params = {
		"timestep":         1,
		"timecycle":        10,
		"beaconNb":         10,
		"threshold":        10,
	}
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
		# neighbor registration
		self.neighbors = {}
		# localizeation
		self.listeningTimer = 0
		self.tdoaCalc = None
		# "unlocalized" status
		self.bestAnchors = None
		# "localized" status
		x, y, z = position
		self.positionEstimates = [(x, y, z, 0)] if localized else []
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
			if self.beaconCount == RLSNode.params["beaconNb"]:
				self.status = "LR"
			delay = time - self.beaconTime
			self.beaconTime = None
			return self.name + " beacon " + str(self.anchorLevel) + " " + str(self.beaconCount) + " " + str(delay)
		
		if time / RLSNode.params["timestep"] > self.slotTimer:
			self.slotTimer += RLSNode.params["timecycle"]
			print str(time) + " " + self.name + " ping " + self.status
			
			if self.status == "UP" and self.bestAnchors is not None:
				self.status = "UA"
				return ""
			
			if time > self.listeningTimer:
				
				if self.status == "UA":
					return self.name + " request " + " ".join(self.bestAnchors)
				
				if self.status == "LN":
					self.status = "LR"
					x, y, z, e = self.positionSynthesis()
					return self.name + " position " + str(x) + " " + str(y) + " " + str(z) + " " + str(e)
		
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
			position = (x, y, z)
			error = float(data[3])
			# if node is unlocalized, attempt to find a better anchor set
			if self.status in ["UP", "UA"]:
				self.findAnchors(sender, position, error)
			# add to the list of neighbor
			self.neighbors[sender] = (position, error)
			# revert to "unlocalized-passive" if needed
			if self.status == "UA" and time/RLSNode.params["timestep"] > self.slotTimer - RLSNode.params["timecycle"]/2:
				self.status = "UP"
		
		if subject == "request":
			if self.status == "LR" and self.name in data:
				self.status = "A"
				i = data.index(self.name)
				self.anchorLevel = i
				self.anchorMaster = data[i-1 % 4]
				p, e = self.neighbors[self.anchorMaster]
				d = distance(self.position, p)
				self.masterDelay = d / self.simParams["sos"]
				if i == 0:
					self.beaconTime = time
					self.beaconCount = 1
		
		if subject == "beacon":
			level = int(data[0])
			count = int(data[1])
			delay = float(data[2])
			if self.status == "A":
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
				self.listeningTimer = time + 2 * RLSNode.params["timestep"]
				# first beacon: new calculator
				if count == 1 and level == 0:
					self.tdoaCalc = TDOACalculator()
				elif self.tdoaCalc is None:
					return
				# first cycle: register anchors
				if count == 1:
					position, error = self.neighbors[sender]
					x, y, z = position
					self.tdoaCalc.addAnchor(level, x, y, z)
				else:
					for a in self.tdoaCalc.anchorPositions:
						if a is None:
							self.tdoaCalc = None
							return
				# all cycles: register data
				self.tdoaCalc.addDataPoint(count, level, time, delay)
				# final beacon: calculate position
				if count == RLSNode.params["beaconNb"] and level == 3:
					msg, x, y, z, e = self.tdoaCalc.calculatePosition(self.simParams["sos"])
					self.tdoaCalc = None
					print self.name + " calculating: " + msg
					if msg == "ok" and e < RLSNode.params["threshold"]:
						self.positionEstimates.append((x,y,z, e))
						self.status = "LN"
						for p in self.positionEstimates:
							print p
	
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
			ex, ey, ez, ee = self.positionSynthesis()
			plot.scatter(ex, ey, ez, c=color, marker='+')
			plot.scatter(ex, ey, ez, c=(0,0,0,0.2), marker='o', lw=0, s=20*ee)
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
	
	def findAnchors(self, newNode, position, error):
		# dumb solution: select the last four neighbors
		nb = self.neighbors.keys()
		while newNode in nb:
			nb.remove(newNode)
		if len(nb) >= 3:
			self.bestAnchors = nb[-3:]
			self.bestAnchors.append(newNode)
	
	def positionSynthesis(self):
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
	