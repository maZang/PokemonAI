from learn import Learner
from learn import UtilFunction

class ValueIterationLearner(Learner):
	'''
	Trains by learning the optimal value function from a given MDP with Dynamic programming.
	Then uses it to come up with a policy to solve the main problem.
	'''

	def __init__(self, mdp, discount=0.9, iterations=1000):
		'''
		Initializes the ValueIterationLearner. Gives it a Markov Decision Process,
		and then it computes the optimal value function with synchronous dynamic programming.
		'''
		self.mdp = mdp 
		self.discount = discount
		self.convergence = False
		values = UtilFunction()
		for _ in xrange(iterations):
			nextValues = UtilFunction()
			convergence = 0 # if convergence == 0 at the end of this loop, the mdp has converged
			for state in mdp.getStates():
				if mdp.isEndState(state):
					nextValues[state] = 0.
					continue
				nextValues[state] = float('-inf')
				for action in mdp.getActions(state):
					actionVal = 0.
					for (nextState, prob) in mdp.getTransitionProbabilities(state, action):
						reward = mdp.getReward(state, action, nextState)
						actionVal += prob * (reward + discount * values[nextState])
					nextValues[state] = max(nextValues[state], actionVal)
				if (values[state] != nextValues[state]):
					convergence += 1
			if convergence == 0:
				self.convergence = True 
				break
			values = nextValues 
		self.values = values

	def getValue(self, state):
		'''
		Gets the value of the value function at the given state
		'''
		return self.values[state]

	def getQValue(self, state, action):
		'''
		Computes q(s,a)
		'''
		return sum([prob * (self.mdp.getReward(state, action, nextState) + self.discount * self.values[nextState])
			for (nextState, prob) in self.mdp.getTransitionProbabilities(state, action)])

	def getOptimalAction(self, state):
		if self.mdp.isEndState(state):
			return None
		return max([(action, self.getQValue(state, action)) for action in self.mdp.getActions(state)], 
			key = lambda x: x[1])[0]

	def getAction(self, state):
		'''
		Computes the action from the given state
		'''
		return self.getOptimalAction(state)

	def update(self, state, action, nextState, reward):
		'''
		Value Iteration agent learns from the MDP, not from experience
		'''
		return 

	def updateEpisodeNumber(self):
		'''
		Called by environment to set the beginning of a new episode
		'''
		return