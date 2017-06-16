from SimEnvironment import SimEnvironment
from UWNode import UWNode

class TestNode(UWNode):
	"""Class for testing node functionalities
	Sends messages back and forth
	"""
	def __init__(self, nb):
		"""Create a node
		nb          -- index of the node, used to give it a name
		"""
		UWNode.__init__(self, "node"+str(nb))
		self.readyToSend = False
		self.messageCounter = 0
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		if self.readyToSend:
			message = "from " + self.name + " #" + str(self.messageCounter)
			print self.name + " sent message '" + message + "' at time " + str(time)
			self.readyToSend = False
			self.messageCounter += 1
			return message
		else:
			return ""
	
	def receive(self, time, message):
		"""Function called when a message broadcast by another node arrives at the node
		time        -- date of reception (s)
		message     -- message received
		"""
		print self.name + " received message '" + message + "' at time " + str(time)
		self.readyToSend = True

node1 = TestNode(1)
node2 = TestNode(2)
node3 = TestNode(3)

sim = SimEnvironment((1000,1000,200), {"tick":0.1})
sim.addNode(node1)
sim.addNode(node2)
sim.addNode(node3)

node1.readyToSend = True

sim.run(2)