from learner.superviser.supervisernetwork import PokemonNetwork
import tensorflow as tf
import numpy as np

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

class PokemonAINetwork(object):

	def _add_placeholder(self):
		self.poke_placeholders = [tf.placeholder(tf.int32, shape=(None, self.config.poke_descriptor_size)) for _ in range(12)]
		self.x_data_placeholder = tf.placeholder(tf.float32, shape=(None, self.config.number_non_embedding))
		self.last_move_placeholder = tf.placeholder(tf.int32, shape=(None, self.config.last_move_data))
		self.action_placeholder = tf.placeholder(tf.int32, shape=(None,))
		self.targetQ_placeholder = tf.placeholder(tf.float32, shape=(None,))
		self.possible_actions_placeholder = tf.placeholder(tf.int32, shape=(None,self.config.max_actions,2))
		self.initial_state = tf.placeholder(tf.float32, shape=(self.config.memory_layer_depth, 2, None, self.config.memory_layer_size))
		self.dropout_placeholder = tf.placeholder(tf.float32)
		self.batch_size = tf.placeholder(tf.int32)
		self.num_steps = tf.placeholder(tf.int32)

	def _add_embedding(self):
		'''
		Extracts the embeddings out of the current vector
		Assumes the encoding is like
		[Poke1, Move1, Move2, Move3, Move4, Item1, Status1] * 12 + [Poke1Hp] * 12
		Note, ids are shared between pokemon, moves, items, and statuses -- ENSURE THIS IN ENCODING

		Final output is a list with each element of shape
			 [None, poke_descriptor_size, embedding_size]
		'''
		with tf.device('/cpu:0'):
			all_embeddings = tf.get_variable('poke_embeddings', shape=(self.config.number_pokemon+self.config.number_moves+\
				self.config.number_items+self.config.number_status, self.config.embedding_size))
			self.all_embeddings = all_embeddings
			self.embedding_inputs = [tf.reshape(tf.nn.embedding_lookup(all_embeddings, placeholder),
				(-1, self.config.poke_descriptor_size, self.config.embedding_size))
				for placeholder in self.poke_placeholders]
			self.last_move_embeddings = tf.nn.embedding_lookup(all_embeddings, self.last_move_placeholder)

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
		with tf.variable_scope('Split'):
			splits = tf.split(self.x_data_placeholder, self.config.num_concat, 1)
		with tf.variable_scope('PokeConvNet'):
			# Conv net layer that uses kernels of different widths to get average representations
			self.embedding_inputs = [tf.expand_dims(embedding_input,-1) for embedding_input in self.embedding_inputs]
			layers = [[] for _ in self.embedding_inputs]
			for idx,kernel_height in enumerate(self.config.kernels_poke):
				conv_filter = tf.get_variable('PokeKernelHeight' + str(kernel_height),
									shape=(kernel_height,self.config.embedding_size,1,self.config.feature_maps_poke[idx]))
				conv_layers = [tf.nn.conv2d(embedding_input,conv_filter,strides=[1,1,1,1],padding='VALID')
								for embedding_input in self.embedding_inputs]
				new_height = self.config.poke_descriptor_size - kernel_height + 1
				pools = [tf.nn.max_pool(tf.nn.relu(conv), [1,new_height,1,1], [1,1,1,1], 'VALID') for conv in conv_layers]
				[layer.append(tf.squeeze(pool, [1,2])) for layer,pool in zip(layers,pools)]
			conv_outputs = [tf.concat(layer,1) for layer in layers] # each output is of size [None,sum(feature_maps)]
			conv_outputs = [tf.concat((layer,split),1) for layer,split in zip(conv_outputs,splits)]
		with tf.variable_scope('OwnTeamConvNet'):
			own_player_conv = tf.expand_dims(tf.stack(conv_outputs[:6], axis=1), -1)
			layers = []
			for idx,kernel_height in enumerate(self.config.kernels_team):
				conv_filter = tf.get_variable('OwnTeamKernelHeight' + str(kernel_height),
								shape=(kernel_height,np.sum(self.config.feature_maps_poke)+1,1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.nn.relu(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool, [1,2]))
			own_team_output = tf.concat(layers, 1)
		with tf.variable_scope('OppTeamConvNet'):
			opp_player_conv = tf.expand_dims(tf.stack(conv_outputs[6:], axis=1), -1)
			layers = []
			for idx,kernel_height in enumerate(self.config.kernels_team):
				conv_filter = tf.get_variable('OppTeamKernelHeight' + str(kernel_height),
								shape=(kernel_height,np.sum(self.config.feature_maps_poke)+1,1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.nn.relu(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool, [1,2]))
			opp_team_output = tf.concat(layers, 1)
		with tf.variable_scope('HighwayNet'):
			last_move_concat = tf.reshape(self.last_move_embeddings, (-1, self.config.last_move_data*self.config.embedding_size))
			output = tf.concat([own_team_output,opp_team_output,last_move_concat], 1)
			highway_size = 2 * sum(self.config.feature_maps_team) + self.config.last_move_data*self.config.embedding_size
			w_t = tf.get_variable('weight_transform', shape=(highway_size,highway_size))
			b_t = tf.get_variable('bias_transform', shape=(highway_size,))
			transform = tf.sigmoid(tf.matmul(output, w_t) + b_t)
			w = tf.get_variable('weight', shape=(highway_size,highway_size))
			b = tf.get_variable('bias', shape=(highway_size,))
			a = tf.nn.relu(tf.matmul(output, w) + b)
			carry = 1.0 - transform
			highway_output = transform * a + carry * output
		with tf.variable_scope('MemoryLayer'): # uses an LSTM to remember previous moves
			def get_cell():
				cell = tf.contrib.rnn.BasicLSTMCell(self.config.memory_layer_size)
				dropout_cell = tf.contrib.rnn.DropoutWrapper(cell, input_keep_prob=self.dropout_placeholder,
					output_keep_prob=self.dropout_placeholder)
				return cell
			stacked_cell = tf.contrib.rnn.MultiRNNCell([get_cell() for _ in range(self.config.memory_layer_depth)])
			lstm_input = tf.reshape(highway_output, (self.batch_size, self.num_steps, highway_size))
			l = tf.unstack(self.initial_state, axis=0)
			tuple_state = tuple([tf.contrib.rnn.LSTMStateTuple(l[idx][0], l[idx][1]) for idx in range(self.config.memory_layer_depth)])
			rnn_output, self.final_state = tf.nn.dynamic_rnn(stacked_cell,lstm_input,initial_state=tuple_state)
			rnn_output = tf.reshape(rnn_output,shape=(-1,self.config.memory_layer_size))
		with tf.variable_scope('OutputQ'):
			streamA,streamV = tf.split(rnn_output,2,1)
			AW = tf.get_variable('AW', shape=(self.config.memory_layer_size//2, self.config.number_classes))
			VW = tf.get_variable('VW', shape=(self.config.memory_layer_size//2, 1))
			Ab = tf.get_variable('Ab', shape=(self.config.number_classes,))
			Vb = tf.get_variable('Vb', shape=(1,))
			advantage = tf.matmul(streamA,AW) + Ab
			value = tf.matmul(streamV,VW) + Vb 
			self.q_out = value + tf.subtract(advantage, tf.reduce_mean(advantage,axis=1,keep_dims=True))

	def _add_loss(self):
		possible_actions = tf.squeeze(tf.slice(self.possible_actions_placeholder, [0,0,1], [-1,-1,-1]), axis=2)
		self.filtered_q = tf.gather_nd(self.q_out, self.possible_actions_placeholder) * tf.cast((possible_actions > 0), tf.float32) + self.config.lower_bound * tf.cast((possible_actions <= 0), tf.float32)
		row_selector = tf.range(tf.shape(self.possible_actions_placeholder, out_type=tf.int32)[0], dtype=tf.int32)
		col_selector =  tf.cast(tf.argmax(self.filtered_q,1), tf.int32)
		indexes_nd = tf.stack((row_selector, col_selector), -1)
		self.predictions = tf.gather_nd(possible_actions, indexes_nd)
		actions_onehot = tf.one_hot(self.action_placeholder, self.config.number_classes,dtype=tf.float32)
		q_scores = tf.reduce_sum(tf.multiply(self.q_out, actions_onehot), axis=1)
		targets = tf.reshape(self.targetQ_placeholder, [-1])
		td_error = tf.square(targets - q_scores)
		with tf.variable_scope('loss'):
			mask_lower = tf.zeros([self.batch_size, self.num_steps // 2])
			mask_upper = tf.ones([self.batch_size, self.num_steps // 2])
			mask = tf.reshape(tf.concat([mask_lower, mask_upper], 1), [-1])
			self.loss = tf.reduce_mean(tf.multiply(mask, td_error))

	def _add_optimizer(self):
		with tf.variable_scope('opt'):
			optimizer = tf.train.AdamOptimizer(self.config.learning_rate)
			self.train_op = optimizer.minimize(self.loss)

	def _build_graph(self):
		self._add_placeholder()
		self._add_embedding()
		self._network_model()
		self._add_loss()
		self._add_optimizer()

	def __init__(self, config, scope='POKEMON'):
		self.config = config
		with tf.variable_scope(scope):
			self._build_graph()

	def init_hidden_state(self, batch_size):
		return np.zeros((self.config.memory_layer_depth, 2, batch_size, self.config.memory_layer_size))
