from learner.learn import Learner
from learner.learn import UtilFunction
# lib imports
import random as random

class QLearner(Learner):
	'''
	Q learning class. Learns q(s,a) for each state, action pair
	'''

	def __init__(self, environment=None, alpha=1.0, epsilon=0.1, discount=0.8, trainingEpisodes=10):
		'''
		alpha - learning rate
		epsilon - exploration factor
		discount - future reward discount
		trainingEpisodes - no more learning after set number of episodes
		'''
		self.alpha = alpha
		self.epsilon = epsilon
		self.discount = discount
		self.trainingEpisodes = trainingEpisodes
		self.qValues = UtilFunction()
		self.environment = environment
		self.episodeNumber = 0

		self.actions = []

	def getQValue(self,state,action):
		return self.qValues[(state,action)]

	def getValue(self, state):
		'''
		Returns the value of the given state
		'''
		if len(actions) == 0:
			return 0.0
		return max([self.getQValue(state,action) for action in self.actions])

	def getOptimalAction(self, state):
		'''
		Computes the optimal action as the max_a q(s,a) for a given state a. Returns a random choice
		if multiple actions have the same value
		'''
		actionVals = [(action, self.getQValue(state, action)) for action in self.actions]
		if len(actionVals) == 0:
			return None
		maxVal = max([x[1] for x in actionVals])
		maxActions = [x[0] for x in actionVals if x[1] == maxVal]
		return random.choice(maxActions)

	def getAction(self, state, actions):
		'''
		Gets an action depending on whether we are following greedy policy or exploratory policy
		'''
		self.actions = actions
		if len(self.actions) == 0:
			return None
		if (random.random() < 1. - self.epsilon) or self.episodeNumber > self.trainingEpisodes:
			# choose the best action
			action = self.getOptimalAction(state)
		else:
			# choose a random action
			action = random.choice(self.actions)
		return action

	def update(self, state, action, nextState, reward):
		'''
		Updates the policy after observing a state, action => nextState, reward pair.
		'''
		if self.episodeNumber > self.trainingEpisodes:
			return
		self.qValues[(state,action)] = self.qValues[(state,action)] +\
				self.alpha * (reward + self.discount * self.getValue(nextState) - self.qValues[(state,action)])

	def updateEpisodeNumber(self):
		'''
		Called by environment to set the beginning of a new episode
		'''
		self.episodeNumber += 1