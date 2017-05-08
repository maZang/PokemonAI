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

class PokemonAINetwork(object):

	def _add_placeholder(self):
		self.poke_placeholders = [tf.placeholder(tf.int32, shape=(None, self.config.poke_descriptor_size)) for _ in range(12)]
		self.x_data_placeholder = tf.placeholder(tf.float32, shape=(None, self.config.number_non_embedding))
		self.last_move_placeholder = tf.placeholder(tf.int32, shape=(None, self.config.last_move_data))
		self.action_placeholder = tf.placeholder(tf.int32, shape=(None,))
		self.targetQ_placeholder = tf.placeholder(tf.int32, shape=(None,))
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
			self.embedding_inputs = [tf.reshape(tf.nn.embedding_lookup(all_embeddings, placeholder),
				(-1, self.config.poke_descriptor_size, self.config.embedding_size))
				for placeholder in self.poke_placeholders]
			self.last_move_embeddings = tf.nn.embedding_lookup(all_embeddings, self.last_move_placeholder)

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
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
				pools = [tf.nn.max_pool(tf.tanh(conv), [1,new_height,1,1], [1,1,1,1], 'VALID') for conv in conv_layers]
				[layer.append(tf.squeeze(pool)) for layer,pool in zip(layers,pools)]
			conv_outputs = [tf.concat(layer,1) for layer in layers] # each output is of size [None,sum(feature_maps)]
		with tf.variable_scope('OwnTeamConvNet'):
			own_player_conv = tf.expand_dims(tf.stack(conv_outputs[:6], axis=1), -1)
			layers = []
			for idx,kernel_height in enumerate(self.config.kernels_team):
				conv_filter = tf.get_variable('OwnTeamKernelHeight' + str(kernel_height),
								shape=(kernel_height,np.sum(self.config.feature_maps_poke),1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.tanh(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool))
			own_team_output = tf.concat(layers, 1)
		with tf.variable_scope('OppTeamConvNet'):
			opp_player_conv = tf.expand_dims(tf.stack(conv_outputs[6:], axis=1), -1)
			layers = []
			for idx,kernel_height in enumerate(self.config.kernels_team):
				conv_filter = tf.get_variable('OppTeamKernelHeight' + str(kernel_height),
								shape=(kernel_height,np.sum(self.config.feature_maps_poke),1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.tanh(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool))
			opp_team_output = tf.concat(layers, 1)
		with tf.variable_scope('HighwayNet'):
			concat_data = tf.reshape(self.x_data_placeholder,(-1,self.config.number_non_embedding))
			last_move_concat = tf.reshape(self.last_move_embeddings, (-1, self.config.last_move_data*self.config.embedding_size))
			output = tf.concat([own_team_output,opp_team_output,concat_data,last_move_concat], 1)
			highway_size = 2 * sum(self.config.feature_maps_team) + self.config.number_non_embedding +\
							 self.config.last_move_data*self.config.embedding_size
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
			self.initial_state = stacked_cell.zero_state(self.batch_size, tf.float32)
			rnn_output, self.final_rnn_state = tf.nn.dynamic_rnn(stacked_cell,lstm_input,initial_state=self.initial_state)
			rnn_output = tf.reshape(rnn_output,shape=(-1,self.config.memory_layer_size))
		with tf.variable_scope('OutputQ'):
			score_w = tf.get_variable('score_w', shape=(self.config.memory_layer_size, self.config.number_classes))
			score_b = tf.get_variable('score_b', shape=(self.config.number_classes,))
			self.q_out = tf.tanh(tf.matmul(rnn_output, score_w) + score_b)

	def _add_loss(self):
		self.predictions = tf.argmax(self.scores,1)
		actions_onehot = tf.one_hot(self.action_placeholder, self.config.number_classes,dtype=tf.float32)
		q_scores = tf.reduce_sum(tf.multiply(self.q_out, actions_onehot), axis=1)
		targets = tf.reshape(self.targetQ_placeholder, [-1])
		td_error = tf.square(targets - q_scores)
		with tf.variable_scope('loss'):
			mask_lower = tf.zeros([self.batch_size, self.num_steps // 2])
			mask_upper = tf.ones([self.batch_size, self.num_steps // 2])
			mask = tf.reshape(tf.concat(makse_lower, mask_upper), [-1])
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
		self.data_iter = ReplayDataIter(TRAIN, VALIDATION, TEST, lambda x: encode(config, x))
		self.config = config
		with tf.variable_scope(scope):
			self._build_graph()

	def init_hidden_state(self):
		return np.zeros((self.config.memory_layer_depth, 2, sample[0].shape[0], self.config.memory_layer_size))

	def run_epoch(self, epoch_num, session, sample_set, train_op = None, to_print=False):
		dp = self.config.dropout
		total_batches = self.data_iter.number_batches(self.config.batch_size, self.config.num_steps)
		total_loss = []
		if not train_op:
			train_op = tf.no_op()
			dp = 1.

		for i,sample in enumerate(self.data_iter.sample(self.config.batch_size, self.config.num_steps, sample_set)):
			# sample is a list of [poke1matrix, poke2matrix, ..., poke12matrix, other_x_state, y]
			feed_dict1 = {self.poke_placeholders[i] : sample[i] for i in range(12)}
			batch_size = sample[0].shape[0] / self.config.num_steps
			feed_dict_rest = {self.x_data_placeholder: sample[12],
							self.last_move_placeholder: sample[13],
							self.y_placeholder: sample[14],
							self.dropout_placeholder: dp,
							self.batch_size : batch_size,
							self.num_steps : self.config.num_steps}
			feed_dict = {**feed_dict1, **feed_dict_rest}
			loss, _ = session.run([self.loss, train_op], feed_dict=feed_dict)
			total_loss.append(loss)

			if (i % 100) == 0 and to_print:
				print("epoch: [%d] iter: [%d/%d] loss: [%2.5f]" % (epoch_num, i, total_batches, loss))
		return total_loss

	def run_network(self, sess, sample, initial_state=None):
		if not initial_state:
			initial_state = np.zeros((self.config.memory_layer_depth, 2, sample[0].shape[0], self.config.memory_layer_size))
		l = tf.unpack(initial_state, axis=0)
		feed_dict1 = {self.poke_placeholders[i] :  sample[i] for i in range(12)}
		feed_dict_rest = {self.x_data_placeholder: sample[13], self.dropout_placeholder: dp,
						self.batch_size : sample[0].shape[0], self.num_steps : 1,
						self.initial_state: l}
		feed_dict = {**feed_dict1, **feed_dict_rest}
		pred, next_state = sess.run([self.predictions, self.final_rnn_state], feed_dict=feed_dict)
		return pred, next_state

