class MarkovDecisionProcess(object):

	def getStates(self):
		'''
		Returns all the states in a given MDP. Might not be implemented
		for some continuous MDPS
		'''
		raise NotImplementedError('MDP should implement this')

	def getInitialState(self):
		'''
		Returns an initial state
		'''
		raise NotImplementedError('MDP should implement this')

	def getTransitionProbabilities(self, state, action):
		'''
		Gets the transition probabilities for the next state given a current state
		and action. Might not be implemented in all MDPs. Returns (nextState, prob) tuples.
		'''
		raise NotImplementedError('MDP should implement this')

	def getActions(self, state):
		'''
		Returns all the possible actions in this MDP starting from a given state. If state=None, return all actions.
		'''
		raise NotImplementedError('MDP should implement this')

	def getReward(self, state, action, nextState):
		'''
		Returns the expected reward for a given transition, action tuple
		'''
		raise NotImplementedError('MDP should implement this')

	def isEndState(self, state):
		'''
		Returns true if it is a self-absorbing state. Note, if
		getActions(state) returns a list of length 0,
		then isEndState(state) must be true. The converse, however,
		might not always be true.
		'''
		raise NotImplementedError('MDP should implement this')
