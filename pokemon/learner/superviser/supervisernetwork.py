from datautils.replaydataiter import ReplayDataIter
from datautils.parser import encode
import tensorflow as tf
import datautils.const as const
import os, pickle

DATA_FOLDER = 'data/parsed_replays/'
TRAIN = DATA_FOLDER + 'train'
VALIDATION = DATA_FOLDER + 'val'
TEST = DATA_FOLDER + 'test'

class PokemonNetworkConfig(object):

	embedding_size = 100
	poke_descriptor_size = const.POKE_DESCRIPTOR_SIZE # poke id, 4 move ids, item id, status id
	number_non_embedding = const.NON_EMBEDDING_DATA
	number_classes = const.NUMBER_CLASSES # 4 options for each move, +6 options to switch Pokemon, +1 mega-evolve -- ALTERNATIVE, number_moves + number_pokemon + 1 (mega-evolve)
	learning_rate = 1e-3
	max_epochs = 10
	early_stop = 2
	dropout = 0.9
	batch_size = 64
	memory_layer_size = 300
	memory_layer_depth = 3
	number_pokemon = const.NUMBER_POKEMON
	number_moves = const.NUMBER_MOVES
	number_items = const.NUMBER_ITEMS
	number_status = len(const.STATUS_EFFECTS) 
	kernels_poke=[1,2,3,4,5,6,7]
	feature_maps_poke=[50,60,70,80,90,100,110,120]
	kernels_team=[1,2,3,4,5,6]
	feature_maps_team=[50,60,70,80,90,100,110]
	num_steps = 8
	save_folder = 'data/models/'
	model_name = 'supervised_network/'

class PokemonNetwork(object):

	def _add_placeholder(self):
		self.poke_placeholders = [tf.placeholder(tf.int32, shape=(None, poke_descriptor_size)) for _ in range(12)]
		self.x_data_placeholder = tf.placeholder(tf.float32, shape=(None, number_non_embedding))
		self.y_placeholder = tf.placeholder(tf.float32, shape=(None, number_classes))
		self.dropout_placeholder = tf.placeholder(tf.float32)

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
			poke_embeddings = tf.get_variable('poke_embeddings', shape=(self.config.number_pokemon, self.config.embedding_size))
			move_embeddings = tf.get_variable('move_embeddings', shape=(self.config.number_moves, self.config.embedding_size))
			item_embeddings = tf.get_variable('item_embeddings', shape=(self.config.number_items, self.config.embedding_size))
			status_embeddings = tf.get_variable('status_embeddings', shape=(self.config.number_status, self.config.embedding_size))
			self.embedding_inputs = [tf.reshape(tf.nn.embedding_lookup([poke_embeddings,move_embeddings,item_embeddings,
				status_embeddings], placeholder), (-1, self.config.poke_descriptor_size, self.config.embedding_size))
				for placeholder in self.poke_placeholders] 

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
		
		with tf.variable_scope('PokeConvNet'):
			# Conv net layer that uses kernels of different widths to get average representations
			self.embedding_inputs = [tf.expand_dims(embedding_input,-1) for embedding_input in self.embedding_inputs]
			layers = [[] for _ in self.embedding_inputs]
			for idx,kernel_height in enumerate(kernels_poke):
				conv_filter = tf.get_variable('poke_kernel_height:' + str(kernel_height), 
									shape=(kernel_height,self.config.embedding_size,1,self.config.feature_maps_poke[idx]))
				conv_layers = [tf.nn.conv2d(embedding_input,conv_filter,strides=[1,1,1,1],padding='VALID')]
				new_height = self.config.poke_descriptor_size - kernel_height + 1
				pools = [tf.nn.max_pool(tf.tanh(conv), [1,new_height,1,1], [1,1,1,1], 'VALID') for conv in conv_layers]
				layers = [layer.append(tf.squeeze(pool)) for layer,pool in zip(layers,pools)]
			conv_outputs = [tf.concat(layer,1) for layer in layers] # each output is of size [None,sum(feature_maps)]
		with tf.variable_scope('OwnTeamConvNet'):
			own_player_conv = tf.concat(conv_outputs[:6], 0)
			layers = []
			for idx,kernel_height in enumerate(kernels_team):
				conv_filter = tf.get_variable('own_team_kernel_height:' + str(kernel_height),
									shape=(kernel_height,self.config.embedding_size,1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.tanh(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool))
			own_team_output = tf.concat(layers, 1)
		with tf.variable_scope('OppTeamConvNet'):
			opp_player_conv = tf.concat(conv_outputs[6:], 0)
			layers = []
			for idx,kernel_height in enumerate(kernels_team):
				conv_filter = tf.get_variable('opp_team_kernel_height:' + str(kernel_height),
									shape=(kernel_height,self.config.embedding_size,1,self.config.feature_maps_team[idx]))
				conv_layer = tf.nn.conv2d(own_player_conv,conv_filter,strides=[1,1,1,1],padding='VALID')
				new_height = 6 - kernel_height + 1
				pool = tf.nn.max_pool(tf.tanh(conv_layer),[1,new_height,1,1],[1,1,1,1],'VALID')
				layers.append(tf.squeeze(pool))
			opp_team_output = tf.concat(layers, 1)
		with tf.variable_scope('HighwayNet'):
			concat_data = tf.reshape(self.x_data_placeholder,(-1,self.config.number_non_embedding))
			output = tf.concat([own_team_output,opp_team_output,concat_data], 1)
			highway_size = 2 * sum(feature_maps_team) + self.config.number_non_embedding
			w_t = tf.get_variable('weight_transform', shape=(size,size))
			b_t = tf.get_variable('bias_transform', shape=(size,))
			transform = tf.sigmoid(tf.matmul(output, w_t) + b_t)
			w = tf.get_variable('weight', shape=(size,size))
			b = tf.get_variable('bias', shape=(size,))
			a = tf.nn.relu(tf.matmul(output, w) + b)
			carry = 1.0 - transform
			highway_output = transform * a + carry * output 
		with tf.variable_scope('MemoryLayer'): # uses an LSTM to remember previous moves
			cell = tf.nn.rnn_cell.BasicLSTMCell(self.config.memory_layer_size)
			dropout_cell = tf.nn.rnn_cell.DropoutWrapper(cell, input_keep_prof=self.dropout_placeholder,
				output_keep_prob=self.dropout_placeholder)
			stacked_cell = tf.nn.rnn_cell.MultiRnnCell([dropout_cell] * self.config.memory_layer_depth)
			lstm_input = tf.reshape(highway_output, (self.config.batch_size, self.config.num_steps, highway_size))
			self.initial_state = stacked_cell.zero_state(self.config.batch_size, tf.float32)
			rnn_output, self.final_rnn_state = tf.nn.dynamic_rnn(stacked_cell,lstm_input,initial_state=initial_state)
			rnn_output = tf.reshape(rnn_output,shape=(-1,slf.config.memory_layer_size))
		with tf.variable_scope('OutputScores'):
			score_w = tf.get_variable('score_w', shape=(self.config.memory_layer_size, self.config.number_classes))
			score_b = tf.get_variable('score_b', shape=(self.config.number_classes,))
			self.scores = tf.matmul(output, score_w) + score_b

	def _add_loss(self):
		self.predictions = tf.argmax(self.scores,1)
		targets = tf.reshape(self.y_placeholder, [-1])
		with tf.variable_scope('loss'):
			self.loss = tf.reduce_sum(tf.nn.sparse_softmax_cross_entropy_with_logits(self.scores,targets))

	def _add_optimizer(self): 
		with tf.variable_scope('opt'):
			optimizer = tf.train.AdamOptimizer(self.config.learning_rate)
			self.train_op = opt.minimize(self.loss)

	def _build_graph(self):
		self._add_placeholder()
		self._add_embedding()
		self._network_model()
		self._add_loss()
		self._add_optimizer()

	def __init__(self, config):
		self.data_iter = ReplayDataIter(TRAIN, VALIDATION, TEST, lambda x: encode(config, x))
		self.config = config
		self._build_graph()

	def run_epoch(self, epoch_num, session, sample_set, train_op = None, to_print=False):
		dp = self.config.dropout
		total_batches = self.data_iter.number_batches(self.config.batch_size)
		total_loss = []
		if not train_op:
			train_op = tf.no_op()
			dp = 1.

		for i,sample in enumerate(self.data_iter.sample(self.config.batch_size, self.config.num_steps, sample_set)):
			# sample is a list of [poke1matrix, poke2matrix, ..., poke12matrix, other_x_state, y]
			feed_dict1 = {self.poke_placeholders[i] : sample[i] for i in range(12)} 
			feed_dict_rest = {self.x_data_placeholder: sample[13], self.y_placeholder: sample[14],
							self.dropout_placeholder: dp}
			feed_dict = {**feed_dict1, **feed_dict_rest}
			loss, _ = session.run([self.loss, train_op])
			total_loss.append(loss)

			if (i % 100) == 0 and to_print:
				print("epoch: [%d] iter: [%d/%d] loss: [%2.5f]" % (epoch_num, i, total_batches, loss))
		return total_loss 

	def run_network(self, sess, sample, initial_state=None):
		if not initial_state:
			initial_state = np.zeros((self.config.memory_layer_depth, 2, self.config.batch_size, self.config.memory_layer_size))
		l = tf.unpack(initial_state, axis=0)
		feed_dict1 = {self.poke_placeholders[i] :  sample[i] for i in range(12)} 
		feed_dict_rest = {self.x_data_placeholder: sample[13], self.dropout_placeholder: dp}
		feed_dict = {**feed_dict1, **feed_dict_rest}
		pred, next_state = sess.run([self.predictions, self.final_rnn_state])
		return pred, next_state

def trainNetwork():
	config = PokemonNetworkConfig()
	with tf.variable_scope('PokemonNetwork'):
		model = PokemonNetwork(config)
	total_losses = []
	init = tf.initialize_all_variables()
	saver = tf.train.Saver()
	best_validation_loss = float('inf')
	best_validation_epoch = 0

	with tf.Session() as sess:
		start = time.time()
		sess.run(init)
		for epoch_num in range(config.max_epochs):
			epoch_losses = model.run_epoch(epoch_num, sess, 'train', model.train_op, True)
			total_losses.extend(epoch_losses)

			if not os.path.exists(config.save_folder + config.model_name):
				os.makedirs(config.save_folder + model_name)
			if not os.path.exists(config.save_folder + config.model_name + 'weights'):
				os.makedirs(config.save_folder + config.model_name + 'weights')
			saver.save(sess, config.save_folder + model_name + 'weights/model', global_step=epoch_num)

			if not os.path.exists(config.save_folder + config.model_name + 'loss'):
				os.makedirs(config.save_folder + config.model_name + 'loss')
			with open(config.save_folder + config.model_name + 'loss' + '/total_losses.p', 'wb') as f:
				pickle.dump(total_losses, f)
			
			validation_loss = np.mean(model.run_epoch(epoch_num, sess, 'val'))
			if validation_loss < best_validation_loss:
				best_validation_epoch = epoch_num
				best_validation_loss = validation_loss
				print('Best epcoh number: %d' % best_validation_epoch)
			if epoch_num - best_validation_epoch > config.early_stop:
				break
			print('Total time: %d' % time.time() - start)
		# get final test accuraccy
		test_loss = np.mean(model.run_epoch(epoch_num, sess, 'test'))
		print('Final test set loss: %d' % test_loss)


