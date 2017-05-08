from learner.qlearner import QLearner
from learner.learn import UtilFunction
# lib imports
import random as random
import tensorflow as tf

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

class AIConfig(object):
	epsilon = 0.1
	annealing_steps = 10000
	num_episodes = 10000
	save_path = 'data/models/pokemon_ai/'
	update_steps = 10
	tau = 0.001 # update rate for target network
	discount = 1.0
	batch_size = 64
	num_steps = 8

class PokemonShowdownAI(QLearner):
	'''
	QLearner class designed to train with nonlinear approximation functions by using
	both experience replay and a target approximation function
	'''

	def __init__(self, environment, state_processer, network, replayArgs, qlearner_config, name, load_model=False):
		tf.reset_default_graph() # just in case
		self.environment = environment
		self.state_processer = state_processer
		self.replay = ExperienceReplay(**replayArgs)
		self.current_episode_buffer = []
		self.current_step = 0
		self.mainQN = network(qlearner_config, 'MAIN')
		self.targetQN = network(qlearner_config, 'TARGET')
		self.config = qlearner_config
		self.current_state = self.mainQN.init_hidden_state()
		# perform some TF initialization
		self.saver = tf.train.Saver()
		self.sess = tf.Session()
		tfVars = tr.trainable_variables()
		total_vars = len(tfVars)
		self.ops = []
		for idx,var in enumerate(tfVars[0:total_vars//2]):
			self.ops.append(tfVars[idx+total_vars//2].assign(var.value() * qlearner_config.tau + ((1 - qlearner_config.tau) *\
				tfVars[idx+total_vars//2].value())))
		# see if folder exists and if to load a model
		self.save_path = qlearner_config.save_path + name
		if not os.path.exists(self.save_path):
			os.makedirs(self.save_path)
		if load_model:
			checkpoint = tf.train.get_checkpoint_state(self.save_path)
			self.saver.restore(self.sess,checkpoint.model_checkpoint_path)
		init = tf.global_variables_initializer()
		sess.run(init)
		# other variable initialization
		self.epsilon = qlearner_config.epsilon
		self.reward_list = []
		self.update_target()


	def update_target(self):
		[self.sess.run(op) for op in self.ops]
		

	def getAction(self, state):
		'''
		Gets an action depending on whether we are following greedy policy or exploratory policy.

		Mutates current state 
		'''
		feed_dict = {}
		if np.random.rand(1.) < self.config.epsilon:
			next_state = self.sess.run(self.mainQN.final_state, feed_dict=feed_dict)
			action = np.random.choice(self.environment.getActions(state))
		else:
			action, next_state = self.sess.run([self.mainQN.predict, self.mainQN.final_state],
				feed_dict=feed_dict)
			action = action[0]
		self.current_state = next_state 
		return action 


	def train_batch(self):
		self.update_target()
		training_batch = self.replay.sample(self.config.batch_size, self.config.num_steps)
		init_state = self.mainQN.init_hidden_state()
		# run both networks
		feed_dict_main = {}
		Q1_actions = self.sess.run(self.mainQN.predict, feed_dict=feed_dict_main)
		feed_dict_target = {}
		Q2_target = self.sess.run(self.targetQN.Qout, feed_dict=feed_dict_target)

		finished = (1. - training_batch[:,4])
		targetQ = training_batch[:, 2] + (self.config.discount * Q2_target[self.config.batch_size * self.config.num_steps, Q1_actions] * finished)
		feed_dict_train = {}
		_ = sess.run(self.mainQN.opt, feed_dict=feed_dict_train)


	def update(self, state, action, nextState, reward, terminal):
		'''
		Updates the policy after observing a state, action => nextState, reward pair.

		assume, action is an int and reward is a float. Terminal is either 1 (if it is a terminal
		state) or 0 if not
		'''
		self.current_step += 1
		experience_sample = [self.state_processer(state), action, self.state_processer(nextState), reward, terminal]
		self.current_episode_buffer.append(experience_sample)
		if self.current_step % self.config.update_steps == 0:
			self.train_batch()
		if terminal: # only one reward of 1 or -1 at end
			self.reward_list.append(reward)

	def updateEpisodeNumber(self):
		'''
		Called by environment to set the beginning of a new episode
		'''
		self.replay.add(self.current_episode_buffer)
		self.current_episode_buffer = []
		self.episodeNumber += 1
		self.current_state = self.mainQN.init_hidden_state()
