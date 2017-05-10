from learner.qlearner import QLearner
from learner.learn import UtilFunction
from datautils import const
# lib imports
import random as random
import tensorflow as tf
import numpy as np
import os

class ApproxQLearner(QLearner):
	'''
	Learns an approximate q function by learning parameters w such that
	f(w,s') where s' is some feature extraction of the state/action is approximately
	q(s,a)
	'''

	def __init__(self, environment=None, featExtractor=None, **args):
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
		self.buffer = []
		self.buffer_size = buffer_size

	def add(self,exeprience_sample):
		'''
		Adds an experience sample to the buffer
		'''
		if len(self.buffer) + 1 >= self.buffer_size:
			self.buffer[0:1] = [] # remove the first element
		self.buffer.append(exeprience_sample)

	def process_states(self, states):
		lst = zip(*states)
		return [np.concatenate(l,axis=0) for l in lst]

	def process_actions(self, actions):
		return np.array(actions)

	def process_rewards(self, rewards):
		return np.array(rewards)

	def process_terminal(self, terminals):
		return np.array(terminals)

	def sample(self, batch_size, num_steps):
		sampled_episodes = random.sample(self.buffer, batch_size)
		sampled_traces = [[] for _ in range(5)]
		for ep in sampled_episodes:
			point = np.random.randint(0,len(ep)+1-num_steps)
			episode_sequence = zip(*ep[point:point+num_steps])
			sampled_traces[0].append(self.process_states(episode_sequence[0]))
			sampled_traces[1].append(self.process_actions(episode_sequence[1]))
			sampled_traces[2].append(self.process_states(episode_sequence[2]))
			sampled_traces[3].append(self.process_rewards(episode_sequence[3]))
			sampled_traces[4].append(self.process_terminal(episode_sequence[4]))
		return [np.concatenate(l, axis=0) for l in sampled_traces]

class AIConfig(object):
	startE = 1.0
	endE = 0.1
	num_episodes = 10000
	save_path = 'data/models/pokemon_ai/'
	update_steps = 10
	tau = 0.001 # update rate for target network
	discount = 1.0
	pre_train_steps = 10000
	annealing_steps = 10000
	# network parameters
	embedding_size = 300
	poke_descriptor_size = const.POKE_DESCRIPTOR_SIZE # poke id, 4 move ids, item id, status id
	number_non_embedding = const.NON_EMBEDDING_DATA
	number_classes = const.NUMBER_CLASSES
	last_move_data = const.LAST_MOVE_DATA
	max_actions = const.MAX_ACTIONS
	learning_rate = 1e-3
	max_epochs = 10
	early_stop = 2
	dropout = 1.0
	batch_size = 64
	memory_layer_size = 500
	memory_layer_depth = 3
	number_pokemon = const.NUMBER_POKEMON
	number_moves = const.NUMBER_MOVES
	number_items = const.NUMBER_ITEMS
	number_status = len(const.STATUS_EFFECTS)
	kernels_poke=[1,2,3,4,5,6,7]
	feature_maps_poke=[10,20,30,30,30,30,30]
	kernels_team=[1,2,3,4,5,6]
	feature_maps_team=[10,20,30,30,30,30]
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
		self.current_state = self.mainQN.init_hidden_state(1)
		# perform some TF initialization
		self.saver = tf.train.Saver()
		gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
		self.sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
		tfVars = tf.trainable_variables()
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
		self.sess.run(init)
		# other variable initialization
		self.epsilon = qlearner_config.startE
		self.stepE = (qlearner_config.startE - qlearner_config.endE) - qlearner_config.annealing_steps
		self.reward_list = []
		self.update_target()


	def update_target(self):
		[self.sess.run(op) for op in self.ops]

	def preprocess_possible_actions(self, actions):
		joiner = np.array([[i for _ in range(actions.shape[1])] for i in range(actions.shape[0])])
		return np.stack([joiner, actions],axis=-1)

	def create_feed_dict(self, sample, network, init_state=None, num_steps=1, feed_dict3=None):
		if feed_dict3 == None:
			feed_dict3 = {}
		if init_state != None:
			feed_dict3[network.initial_state] = init_state
		batch_size = sample[0].shape[0] / num_steps
		feed_dict1 = {network.poke_placeholders[i] : sample[i] for i in range(12)}
		feed_dict2 = {
			network.x_data_placeholder : sample[12],
			network.last_move_placeholder : sample[13],
			network.possible_actions_placeholder : self.preprocess_possible_actions(sample[14]),
			network.dropout_placeholder: 1.0,
			network.batch_size : batch_size,
			network.num_steps : num_steps,
		}
		feed_dict = {**feed_dict1, **feed_dict2, **feed_dict3}
		return feed_dict

	def getAction(self, state):
		'''
		Gets an action depending on whether we are following greedy policy or exploratory policy.

		Mutates current state
		'''
		feed_dict = self.create_feed_dict(self.state_processer(state), self.mainQN, init_state=self.current_state)
		possible_actions = self.sess.run(self.mainQN.possible_actions, feed_dict=feed_dict)
		indexes_nd = self.sess.run(self.mainQN.indexes_nd, feed_dict=feed_dict)
		print(possible_actions)
		print(indexes_nd)
		if random.random() < self.epsilon:
			next_state = self.sess.run(self.mainQN.final_state, feed_dict=feed_dict)
			actions = self.environment.getActions(state).flatten()
			action = np.random.choice(actions[actions > 0])
		else:
			action, next_state = self.sess.run([self.mainQN.predictions, self.mainQN.final_state],
				feed_dict=feed_dict)
			action = action[0]
		self.current_state = next_state
		return action


	def train_batch(self):
		self.update_target()
		training_batch = self.replay.sample(self.config.batch_size, self.config.num_steps)
		batch_size = training_batch[2][0].shape[0]
		init_state = self.mainQN.init_hidden_state(batch_size)
		# run both networks
		feed_dict_main = self.create_feed_dict(training_batch[2], self.mainQN, init_state=init_state,
				num_steps=self.config.num_steps)
		Q1_actions = self.sess.run(self.mainQN.predictions, feed_dict=feed_dict_main)
		feed_dict_target = self.create_feed_dict(training_batch[2], self.targetQN, init_state=init_state,
				num_steps=self.config.num_steps)
		Q2_target = self.sess.run(self.targetQN.q_out, feed_dict=feed_dict_target)

		finished = (1. - training_batch[:,4])
		targetQ = training_batch[:, 2] + (self.config.discount * Q2_target[self.config.batch_size * self.config.num_steps, Q1_actions] * finished)
		feed_dict3 = {
			self.mainQN.targgetQ : targetQ,
			self.mainQN.action_placeholder : training_batch[:,1]
		}
		feed_dict_train = self.create_feed_dict(training_batch[0], self.mainQN, init_state=init_state,
				num_steps=self.config.num_steps, feed_dict3=feed_dict3)
		_ = self.sess.run(self.mainQN.train_op, feed_dict=feed_dict_train)


	def update(self, state, action, nextState, reward, terminal):
		'''
		Updates the policy after observing a state, action => nextState, reward pair.

		assume, action is an int and reward is a float. Terminal is either 1 (if it is a terminal
		state) or 0 if not
		'''
		if self.epsilon > self.config.endE:
			self.epsilon -= self.stepE
		self.current_step += 1
		experience_sample = [self.state_processer(state), action, self.state_processer(nextState), reward, terminal]
		self.current_episode_buffer.append(experience_sample)
		if self.current_step % self.config.update_steps == 0 and self.current_step > self.config.pre_train_steps:
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
		self.current_state = self.mainQN.init_hidden_state(1)
