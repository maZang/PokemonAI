import tensorflow as tf
import numpy as np

class PokemonAINetwork3(object):

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
			embedding_size = max(self.config.embedding_sizes)
			all_embeddings = tf.get_variable('poke_embeddings', shape=(self.config.number_pokemon+self.config.number_moves+\
				self.config.number_items+self.config.number_status, embedding_size))
			embedding_inputs = [tf.reshape(tf.nn.embedding_lookup(all_embeddings, placeholder),
				(-1, self.config.poke_descriptor_size, embedding_size))
				for placeholder in self.poke_placeholders]
			self.embedding_inputs = []
			for embedding_input in embedding_inputs:
				vecs = []
				for i,size in enumerate(self.config.embedding_sizes):
					vecs.append(tf.squeeze(tf.slice(embedding_input, [0,i,0], [-1,1,size]), [1]))
				self.embedding_inputs.append(vecs)
			last_move_embeddings = tf.nn.embedding_lookup(all_embeddings, self.last_move_placeholder)
			self.last_move_embeddings = tf.slice(last_move_embeddings, [0,0,0], [-1,-1,self.config.embedding_size_move])

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
		with tf.variable_scope('Split'):
			splits = tf.split(self.x_data_placeholder, self.config.num_concat, 1)
			pokemon_mix = [embedding_input[0] for embedding_input in self.embedding_inputs]
			item_mix = [embedding_input[5] for embedding_input in self.embedding_inputs]
			status_mix = [embedding_input[6] for embedding_input in self.embedding_inputs]
		with tf.variable_scope('MoveMix'):
			move_mix = []
			for embedding_input in self.embedding_inputs:
				move_vecs = tf.stack(embedding_input[1:5], axis=1)
				move_max = tf.reduce_max(move_vecs, axis=1)
				move_min = tf.reduce_min(move_vecs, axis=1)
				move_mean = tf.reduce_mean(move_vecs, axis=1)
				move_mix.append(tf.concat([move_min, move_max, move_mean], 1))
		with tf.variable_scope('PokemonVectors'):
			pokemon_vectors = []
			for vecs in zip(pokemon_mix, move_mix, item_mix, status_mix):
				pokemon_vectors.append(tf.concat(vecs, 1))
			pokemon_vectors = [tf.multiply(poke_vec, health) for poke_vec, health in zip(pokemon_vectors, splits)]
			own_team_poke = pokemon_vectors[:6]
			opp_team_poke = pokemon_vectors[6:]
		poke_vec_size = self.config.embedding_size_poke + 3 * self.config.embedding_size_move +\
			 self.config.embedding_size_item + self.config.embedding_size_status
		with tf.variable_scope('FCCOwnPoke'):
			for layer in range(self.config.hidden_layers_poke_vecs):
				if layer == 0:
					inp_size = poke_vec_size 
				else:
					inp_size = self.config.hidden_dim_poke_vecs
				W = tf.get_variable('W' + str(layer), shape=(inp_size,self.config.hidden_dim_poke_vecs))
				b = tf.get_variable('b' + str(layer), shape=(self.config.hidden_dim_poke_vecs,))
				own_team_poke = [tf.nn.relu(tf.matmul(poke,W) + b) for poke in own_team_poke]
		# own_team_poke a list of size 6 containing tensors of shape (None, self.confid.hidden_dim_poke_vecs)
		with tf.variable_scope('FCCOppPoke'):
			for layer in range(self.config.hidden_layers_poke_vecs):
				if layer == 0:
					inp_size = poke_vec_size
				else:
					inp_size = self.config.hidden_dim_poke_vecs
				W = tf.get_variable('W' + str(layer), shape=(inp_size,self.config.hidden_dim_poke_vecs))
				b = tf.get_variable('b' + str(layer), shape=(self.config.hidden_dim_poke_vecs,))
				opp_team_poke = [tf.nn.relu(tf.matmul(poke,W) + b) for poke in opp_team_poke]
		summ_size = self.config.hidden_dim_poke_vecs * 4
		with tf.variable_scope('OwnTeamSummarization'):
			own_present_poke, own_team_poke = own_team_poke[0], own_team_poke[1:]
			team_vecs = tf.stack(own_team_poke, axis=1)
			team_max = tf.reduce_max(team_vecs, axis=1)
			team_min = tf.reduce_max(team_vecs, axis=1)
			team_mean = tf.reduce_mean(team_vecs, axis=1)
			own_team_mix = tf.concat([own_present_poke, team_min, team_max, team_mean], 1)
			for layer in range(self.config.hidden_layers_team_sum):
				if layer == 0:
					inp_size = summ_size 
				else:
					inp_size = self.config.hidden_dim_team_sum
				W = tf.get_variable('W' + str(layer), shape=[inp_size,self.config.hidden_dim_team_sum])
				b = tf.get_variable('b' + str(layer), shape=(self.config.hidden_dim_team_sum,))
				own_team_mix = tf.nn.relu(tf.matmul(own_team_mix, W) + b)
		with tf.variable_scope('OppTeamSummarization'):
			opp_present_poke, opp_team_poke = opp_team_poke[0], opp_team_poke[1:]
			team_vecs = tf.stack(opp_team_poke, axis=1)
			team_max = tf.reduce_max(team_vecs, axis=1)
			team_min = tf.reduce_min(team_vecs, axis=1)
			team_mean = tf.reduce_mean(team_vecs, axis=1)
			opp_team_mix = tf.concat([opp_present_poke, team_min, team_max, team_mean], 1)
			for layer in range(self.config.hidden_layers_team_sum):
				if layer == 0:
					inp_size = summ_size 
				else:
					inp_size = self.config.hidden_dim_team_sum
				W = tf.get_variable('W' + str(layer), shape=[inp_size,self.config.hidden_dim_team_sum])
				b = tf.get_variable('b' + str(layer), shape=(self.config.hidden_dim_team_sum,))
				opp_team_mix = tf.nn.relu(tf.matmul(opp_team_mix, W) + b)
		with tf.variable_scope('FCC'):
			last_move_concat = tf.reshape(self.last_move_embeddings, (-1, self.config.last_move_data*self.config.embedding_size_move))
			output = tf.concat([own_team_mix, opp_team_mix, last_move_concat], 1) # size of (None, self.config.hidden_dim_team_sum * 2)
			output_size = 2 * self.config.hidden_dim_team_sum + 2 * self.config.embedding_size_move
			for layer in range(self.config.hidden_layers_battle):
				if layer == 0:
					inp_size = output_size 
				else:
					inp_size = self.config.hidden_dim_battle
				W = tf.get_variable('W' + str(layer), shape=[inp_size, self.config.hidden_dim_battle])
				b = tf.get_variable('b' + str(layer), shape=(self.config.hidden_dim_battle,))
				output = tf.nn.relu(tf.matmul(output, W) + b)
		with tf.variable_scope('MemoryLayer'): # uses an LSTM to remember previous moves
			def get_cell():
				cell = tf.contrib.rnn.BasicLSTMCell(self.config.memory_layer_size)
				dropout_cell = tf.contrib.rnn.DropoutWrapper(cell, input_keep_prob=self.dropout_placeholder,
					output_keep_prob=self.dropout_placeholder)
				return cell
			stacked_cell = tf.contrib.rnn.MultiRNNCell([get_cell() for _ in range(self.config.memory_layer_depth)])
			lstm_input = tf.reshape(output, (self.batch_size, self.num_steps, self.config.hidden_dim_battle))
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
