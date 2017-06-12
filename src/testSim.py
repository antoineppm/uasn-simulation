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
		UWNode.__init__(self, "node"+str(id))
		self.readyToSend = False
	
	def tick(self, time):
		"""Function called every tick, lets the node perform operations
		time        -- date of polling (s)
		Returns a string to be broadcast (if the string is empty, it is not broadcast)
		"""
		if self.readyToSend:
			message = "from " + self.name
			print self.name + " sent message '" + message + "' at time " + str(time)
			self.readyToSend = False
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

sim = SimEnvironment((500,500,100))
sim.addNode(node1)
sim.addNode(node2)

sim.run(10)