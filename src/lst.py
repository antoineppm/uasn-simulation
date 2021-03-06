#!/usr/bin/env python

from parameters import *
from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from PositionCalculator import TOACalculator, TDOACalculator

import numpy as np

class LSTNode(UWNode):
	"""Node class implementing Large Scale TOA"""
	
	slotNumber = 0  # number of time slots in a full cycle
	
	# for analysis
	toaDataX = []
	toaDataY = []
	toaDataZ = []
	tdoaDataX = []
	tdoaDataY = []
	tdoaDataZ = []
	
	def __init__(self, id, position = (-1,-1,0), localized = False):
		"""Create a node
		id          -- unique number identifying the node and its time slot
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		localized   if set to True, the node is an initial anchor
		"""
		name = "node-" + str(id)
		UWNode.__init__(self, name, position)
		# common attributes
		self.status = ["LOCALIZED", "new"] if localized else ["UNLOCALIZED", "waiting"]
		self.slotTimer = id             # timer indicating the next timeslot (unit: timeslot length)
		LSTNode.slotNumber = max(id+1, LSTNode.slotNumber)
		self.neighbors = {}             # associates a  position to each neighbor's name
		# localization
		self.calculator = None
		self.timestamp = 0              # marks the time origin for the call-and-reply process
		self.positionEstimate = position if localized else (0,0,0)
		# unlocalized nodes should be given a position estimate known to be close to their real position, otherwise ToA may be wrong
		
		# experimental TDOA
		self.TDOAtime = 0
		self.TDOAmaster = 0
		self.TDOAcalc = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		
		if time / LST_TIMESLOT >= self.slotTimer:
			self.slotTimer += LSTNode.slotNumber
			timeslotOpen = True
		else:
			timeslotOpen = False
		
		if self.status[0] == "UNLOCALIZED":
			
			if self.status[1] == "waiting":
				pass
			
			if self.status[1] == "ready":
				if timeslotOpen:
					self.status[1] = "localizing"
					self.timestamp = time
					self.calculator = TOACalculator(self.positionEstimate)
					return self.name + " call"
			
			if self.status[1] == "localizing":
				if time > self.timestamp + LST_TIMESLOT:
					msg, position = self.calculator.getPosition()
					print self.name, "localization:", msg, position
					if msg == "ok":
						self.status = ["LOCALIZED", "new"]
						self.positionEstimate = position
						# for data analysis
						LSTNode.toaDataX.append(time)
						LSTNode.toaDataY.append(np.linalg.norm(position - self.position))
						LSTNode.toaDataZ.append(len(self.calculator.anchors))
					else:
						if len(self.calculator.anchors) < len(self.neighbors):
							# not all neighbors replied, try again
							self.status[1] = "ready"
						else:
							# otherwise wait for more neighbors
							self.status[1] = "waiting"
					self.calculator = None
			
		if self.status[0] == "LOCALIZED":
			
			if self.status[1] == "new":
				if timeslotOpen:
					self.status[1] = "idle"
					x, y, z = self.positionEstimate
					return self.name + " position " + str(x) + " " + str(y) + " " + str(z)
			
			if self.status[1] == "idle":
				pass
		
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
			x = float(data[0])
			y = float(data[1])
			z = float(data[2])
			position = np.array([x, y, z])
			# add to the list of neighbor
			self.neighbors[sender] = position
			# change state if applicable
			if self.status == ["UNLOCALIZED", "waiting"] and len(self.neighbors) >= 3:
				self.status[1] = "ready"
			
			# experimental TDOA
			if self.TDOAmaster == sender:
				self.TDOAcalc.addAnchor(sender, position)
				self.TDOAcalc.addDataPoint(sender, 0, (self.TDOAtime, 0))
				msg, position = self.TDOAcalc.getPosition()
				print self.name, "TDOA", msg
				if msg == "ok":
					print " actual position     " + str(self.position)
					print " estimated position  " + str(position)
					print " error               " + str(np.linalg.norm(self.position - position))
					# for data analysis
					LSTNode.tdoaDataX.append(time)
					LSTNode.tdoaDataY.append(np.linalg.norm(position - self.position))
					LSTNode.tdoaDataZ.append(len(self.TDOAcalc.anchors))
				self.TDOAcalc = None
				self.TDOAmaster = None
		
		if subject == "call":
			if self.status[0] == "UNLOCALIZED" and self.calculator is None:
				# experimental TDOA
				self.TDOAmaster = sender
				self.TDOAtime = time
				self.TDOAcalc = TDOACalculator(self.positionEstimate)
			
			if self.status == ["LOCALIZED", "idle"]:
				return self.name + " reply " + sender # this will be transmitted after a delay SIM_TICK
		
		if subject == "reply":
			recipient = data[0]
			if self.status == ["UNLOCALIZED", "localizing"] and recipient == self.name:
				if sender in self.neighbors:
					self.calculator.addAnchor(sender, self.neighbors[sender])
					self.calculator.addDataPoint(sender, 0, (time - self.timestamp, SIM_TICK))
			
			# experimental TDOA
			elif self.TDOAmaster == recipient:
				if sender in self.neighbors:
					self.TDOAcalc.addAnchor(sender, self.neighbors[sender])
					self.TDOAcalc.addDataPoint(sender, 0, (time, SIM_TICK))
		
		return ""
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		mark = {
		    "UNLOCALIZED":  "s",
		    "LOCALIZED":    "^"
		}[self.status[0]]
		color = {
		    "waiting":      "gray",
		    "ready":        "black",
		    "localizing":   "red",
		    "new":          "green",
		    "idle":         "blue"
		}[self.status[1]]
		plot.scatter(x, y, z, c=color, marker=mark, lw=0)
		
		ex, ey, ez = self.positionEstimate
		plot.scatter(ex, ey, ez, c='k', marker='+')
		plot.plot([x,ex], [y,ey], [z,ez], 'k:')