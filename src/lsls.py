#!/usr/bin/env python

from parameters import *
from SimEnvironment import SimEnvironment, distance
from UWNode import UWNode
from PositionCalculator import UPSCalculator

import numpy as np

class LSLSNode(UWNode):
	"""All-purpose node localizing itself using the LSLS scheme"""
	def __init__(self, id, position = (-1,-1,0), localized = False):
		"""Create a node
		name        -- string identifying the node
		position    -- X,Y,Z coordinates of the node (m,m,m) (default -1,-1,0)
		            the default coordinates will be out of bounds of the simulation space, forcing a random assignment
		"""
		name = "node" + "".join(str(id).split())    # making sure the name does not contain any whitespace
		UWNode.__init__(self, name, position)
		self.timer = float('inf')
		self.beaconCount = 0
		self.tdoaCalc = None
		self.master = []
		if localized:
			self.positionEstimate = position
			# self.errorEstimate = 0
			self.status = "LOCALIZED"
			self.level = 1
		else:
			self.positionEstimate = None
			# self.errorEstimate = -1
			self.status = "UNLOCALIZED"
			self.level = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		subject = ""
		data = []
		if time > self.timer:
			if self.status == "UNLOCALIZED":
				pass
			elif self.status == "LISTENING":
				pass
			elif self.status == "LOCALIZED":
				pass
			elif self.status == "CANDIDATE":
				self.status = "CONFIRMING"
				self.timer = time + 2 * self.standardTimer()
				subject = "confirm"
				parent, d = self.master
				data = [self.level, self.candidateTimer(d), parent]
			elif self.status == "CONFIRMING":
				self.status = "ANCHOR"
				self.timer = float('inf') if self.level > 0 else time + (3 * LSLS_WAITFACTOR + 10) * self.standardTimer()
				subject = "anchor"
				parent, d = self.master
				x, y, z = self.positionEstimate
				data = [self.level, x, y, z, parent]
			elif self.status == "ANCHOR":
				subject = "beacon"
				data = [self.beaconCount, self.level, time - self.timer]
				if self.beaconCount == UPS_NUMBER - 1:
					self.status = "LOCALIZED"
					self.level = 1
					self.timer = float('inf')
				elif self.level == 0:
					self.beaconCount += 1
					self.timer += UPS_PERIOD
				else:
					self.timer = float('inf')
		if len(subject) > 0:
			return " ".join([self.name, subject] + [ str(e) for e in data ])
		else:
			return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		Never transmits
		"""
		sp = message.split()
		sender = sp[0]
		subject = sp[1]
		data = sp[2:]
		if subject == "anchor":
			[level, x, y, z, parent] = data
			level = int(level)
			x = float(x)
			y = float(y)
			z = float(z)
			if self.status == "UNLOCALIZED":
				if level == 0:
					self.master.append([(sender, (x,y,z))])
				else:
					for chain in self.master:
						if len(chain) == level and chain[-1][0] == parent:
							chain.append((sender, (x,y,z)))
						if len(chain) == 4:
							self.status = "LISTENING"
							self.tdoaCalc = UPSCalculator()
							for i in xrange(4):
								a, position = chain[i]
								self.tdoaCalc.addAnchor(i, position)
							self.master = chain
			elif self.status == "LISTENING":
				pass
			elif self.status == "LOCALIZED":
				d = distance(self.positionEstimate, (x,y,z))
				if self.level == level + 1 and d <= LSLS_SUBRANGE:
					# LOCALIZED node received a "anchor" message of lower level: becomes candidate
					self.status = "CANDIDATE"
					self.master = (sender, d)
					self.timer = time + self.candidateTimer(d)
			elif self.status == "CANDIDATE":
				d = distance(self.positionEstimate, (x,y,z))
				if level == self.level + 1 and d <= LSLS_SUBRANGE:
					# CANDIDATE node received a "anchor" message of lower level: consider switching
					t = time + self.candidateTimer(d)
					if t < self.timer:
						self.master = (sender, d)
						self.timer = t
				elif level == self.level and parent == self.master[0] and d <= LSLS_SUBRANGE:
					# CANDIDATE node received a concurrent "anchor" message: become next-level candidate, or reset to LOCALIZED if the chain is complete
					if self.level == 3:
						self.status = "LOCALIZED"
						self.level = 1
						self.timer = float('inf')
					else:
						self.level += 1
						self.master = (sender, d)
						self.timer = time + self.candidateTimer(d)
			elif self.status == "CONFIRMING":
				pass    # it should not be possible to receive a "anchor" message with the same parent during the confirmation stage
			elif self.status == "ANCHOR":
				pass
		elif subject == "confirm":
			[level, f, parent] = data
			level = int(level)
			f = float(f)
			if self.status == "UNLOCALIZED":
				pass
			elif self.status == "LISTENING":
				pass
			elif self.status == "LOCALIZED":
				pass
			elif self.status == "CANDIDATE":
				if level == self.level and parent == self.master[0]:
					# CANDIDATE node received a concurrent "confirm" message: abandon, prepare for next round
					self.status = "LOCALIZED"
					self.level = (self.level % 3) + 1
					self.timer = float('inf')
			elif self.status == "CONFIRMING":
				if level == self.level and parent == self.master[0]:
					# CONFIRMING node received a concurrent "confirm" message: consider abandoning
					if self.candidateTimer(self.master[1]) > f:
						self.status = "LOCALIZED"
						self.level = (self.level % 3) + 1
						self.timer = float('inf')
			elif self.status == "ANCHOR":
				pass
		elif subject == "beacon":
			[count, level, delay] = data
			count = int(count)
			level = int(level)
			delay = float(delay)
			if self.status == "UNLOCALIZED":
				self.master = []
			elif self.status == "LISTENING":
				if self.master[level][0] == sender:
					self.tdoaCalc.addDataPoint(level, count, (time, delay))
					if level == 3 and count == UPS_NUMBER - 1:
						# beacon sequence finished, LISTENING node tries to calculate its position
						# import json
						# print json.dumps(self.tdoaCalc.dataArchive, sort_keys=True, indent=4)
						msg, position = self.tdoaCalc.getPosition()
						if msg != "ok":
							# localization failed, revert to UNLOCALIZED status
							self.status = "UNLOCALIZED"
							self.master = []
						else:
							# localization successful, become CANDIDATE level 0
							self.positionEstimate = position
							# self.errorEstimate = e
							self.status = "CANDIDATE"
							self.level = 0
							# calculate the anchor center
							center = sum([ np.array(p) for a,p in self.master ]) / 4
							d = distance(self.positionEstimate, center)
							self.master = ("master", d)
							self.timer = time + self.candidateTimer(d)
			elif self.status == "LOCALIZED":
				self.level = 1
			elif self.status == "CANDIDATE":
				pass
			elif self.status == "CONFIRMING":
				pass
			elif self.status == "ANCHOR":
				parent, d = self.master
				if parent == sender and self.level == level + 1:
					self.timer = time - d/SND_SPEED - delay         # trigger a beacon at next tick, and indicate the time origin to use
					self.beaconCount = count
		return ""
	
	def standardTimer(self):
		"""A duration equal to the max transmission range divided by the speed of sound.
		Multiples of this are used as timers for various stages
		Returns: time (s)
		"""
		r = float(SIM_RANGE)
		v = float(SND_SPEED)
		return r/v
	
	def candidateTimer(self, d):
		"""The timer used during the "CANDIDATE" stage, depends on the position of the parent anchor and the candidate level
		d           -- distance the parent anchor
		Returns: time (s)
		"""
		k = LSLS_WAITFACTOR
		r = float(SIM_RANGE)
		v = float(SND_SPEED)
		# if self.level == 0:
		# 	return k * (r - d) / v
		# else:
		# 	return k * (r - 4*d + 4*d*d/r) / v
		return k * (r - 2*d) / v
	
	def makeMaster(self):
		"""Makes the node start the simulation as a master anchor node
		Should be called on a single localized node
		"""
		self.status = "CONFIRMING"      # necessary to trigger the anchor message
		self.level = 0
		self.master = ("master", 0)
		self.timer = -1
	
	def display(self, plot):
		"""Displays a representation of the node in a 3D plot
		plot        -- matplotlib plot in which the node must display itself
		"""
		x, y, z = self.position
		color, mark = {
			"UNLOCALIZED":     ("black",    'v'),
			"LISTENING":       ("blue",     'v'),
			"LOCALIZED":       ("orange",   '^'),
			"CANDIDATE":       ("orange",   's'),
			"CONFIRMING":      ("orange",   's'),
			"ANCHOR":          ("red",      's')
		}[self.status]
		plot.scatter(x, y, z, c=color, marker=mark, lw=0)
		if self.positionEstimate is not None:
			ex, ey, ez = self.positionEstimate
			plot.scatter(ex, ey, ez, c=color, marker='+')
			# plot.scatter(ex, ey, ez, c=(0,0,0,0.2), marker='o', lw=0, s=20*self.errorEstimate)
			plot.plot([x,ex], [y,ey], [z,ez], 'k:')
