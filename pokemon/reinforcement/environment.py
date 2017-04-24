class Environment(object):
	'''
	Abstract class that represents the environment for the
	Reinforcement Learning agent
	'''

	def getCurrentState(self):
		'''
		Gets the current state of the environment.
		'''
		raise NotImplementedError('Environment should implement this')

	def getActions(self, state=None):
		'''
		Returns the actions possible for the current state. If state=None, return all actions.
		'''
		raise NotImplementedError('Environment should implement this')

	def reset(self):
		'''
		Resets the environment to the start state
		'''
		raise NotImplementedError('Environment should implement this')

	def update(self, action):
		'''
		Updates the state based upon the current state and action. Returns the new state
		and a reward
		'''
		raise NotImplementedError('Environment should implement this')

	def isEndState(self):
		'''
		Checks if it is an end state, e.g. the episode is over
		'''
		raise NotImplementedError('Environment should implement this')