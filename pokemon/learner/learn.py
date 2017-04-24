import cPickle as pickle
import os, errno

DATA_FOLDER = 'learners/'

def loadLearner(filename):
	try: 
		with open(DATA_FOLDER + filename + ".p", 'rb') as f:
			learner = pickle.load(f)
	except:
		learner = None 
	return learner

class Learner(object):
	'''
	Represents an abstract reinforcement learner
	'''

	def getAction(self, state):
		'''
		Returns the action from a given state following the learner's optimal/exploratory policy.
		Returns None if terminal.
		'''
		raise NotImplementedError('Learner should implement this')

	def getOptimalAction(self, state):
		'''
		Returns the optimal action from a given state following the learner's optimal policy.
		Returns None if terminal.
		'''
		raise NotImplementedError('Learner should implement this')

	def update(self, state, action, nextState, reward):
		'''
		Environment calls this to update the agent for online learning
		'''
		raise NotImplementedError('Learner should implement this')

	def updateEpisodeNumber(self):
		'''
		Called by environment to set the beginning of a new episode
		'''
		raise NotImplementedError('Learner should implement this')

	def save(self, filename):
		'''
		Saves the learner as a pickle file
		'''
		filename = DATA_FOLDER + filename
		if not os.path.exists(os.path.dirname(filename)):
			try:
				os.makedirs(os.path.dirname(filename))
			except OSError as exc:
				if exc.errno != errno.EEXIST:
					raise 
		with open(filename + ".p", 'wb') as f:
			pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)


class UtilFunction(object):
	'''
	Utility function for representing value and q functions
	'''

	def __init__(self):
		self._function = {}

	def __getitem__(self, idx):
		self._function.setdefault(idx, 0)
		return self._function.__getitem__(idx)

	def __setitem__(self, key, item):
		return self._function.__setitem__(key, item)

class FeatureExtractor(object):
	'''
	Abstract class that represents a generic feature extractor. It is specific to certain
	types of learners and holds the weights for function approximation
	'''

	def getValue(self, state, action):
		raise NotImplementedError('FeatureExtractor should implement this')

	def update(self, state, action, amount):
		raise NotImplementedError('FeatureExtractor should implement this')

