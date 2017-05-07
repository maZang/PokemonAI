from learner.superviser.supervisernetwork import PokemonNetwork
import tensorflow as tf

class AIEncoder(object):

	def action_id(self, action):
		'''
		Returns the action id
		'''
		raise NotImplementedError('AIEncoder should implement this')

	def encode_state(self, state):
		'''
		Returns the state vectors
		'''
		raise NotImplementedError('AIEncoder should implement this')

class PokemonAINetwork(PokemonNetwork):

	def __init__(self, config, encoder):
		PokemonNetwork.__init__(self, config)
		self.encoder = encoder
		self.current_state = None 

	def reset_current_state(self):
		self.current_state = None 

	def getValue(self, state, actions):
		pred, _ = self.run_network()

	def getQValue(self, state, action):
		pred, next_state = self.run_network()
		raise NotImplementedError('FeatureExtractor should implement this')

	def update(self, state, action, amount):
		raise NotImplementedError('FeatureExtractor should implement this')
