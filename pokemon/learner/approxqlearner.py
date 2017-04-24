from qlearner import QLearner	
from learn import UtilFunction
# lib imports
import random as random

class ApproxQLearner(QLearner):
		'''
		Learns an approximate q function by learning parameters w such that
		f(w,s') where s' is some feature extraction of the state/action is approximately 
		q(s,a)
		'''

		def __init__(self, environment, featExtractor=None, **args):
			if featExtractor == None:
				raise ValueError('Must have a feature extractor as part of config')
			self.extractor = featExtractor(environment)
			QLearner.__init__(self, environment	, **args)

		def getQValue(self, state, action):
			return self.extractor.getValue(state, action)

		def update(self, state, action, nextState, reward):
			diff = reward + self.discount * self.getValue(state) - self.getQValue(state, action)
			self.extractor.update(state, action, self.alpha * diff)

class ExperienceReplay(object):
	'''
	Class to hold samples of experience which are then used to train
	'''
	def __init__(self, buffer_size=100000):
		self.buffer = buffer 
		self.buffer_size = buffer_size 

	def add(self,exeprience_sample):
		'''
		Adds an experience sample to the buffer
		'''
		if len(self.buffer) + 1 >= self.buffer_size:
			self.buffer[0:1] = [] # remove the first element 
		self.buffer.append(exeprience_sample)

	def addAll(self, experience_samples):
		'''
		Adds many experience samples to the buffer
		'''
		if len(self.buffer) + len(experience_samples) >= self.buffer_size:
			self.buffer[0:len(experience_samples) + len(self.buffer) - self.buffer_size] = []
		self.buffer.extend(experience_samples)

	def sample(self, size):
		return random.sample(self.buffer,size)


class BatchApproxQLearner(ApproxQLearner):
	'''
	QLearner class designed to train with nonlinear approximation functions by using
	both experience replay and a target approximation function
	'''

	def __init__(self, environment, extractorArgs, replayArgs, **args):
		ApproxQLearner.__init__(environment, **args)

	def update(self, state, action, nextState, reward):
		pass 