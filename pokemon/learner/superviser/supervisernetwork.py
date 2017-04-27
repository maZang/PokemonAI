from datautils.replaydataiter import ReplayDataIter
from datautils.parser import encode
import tensorflow as tf

DATA_FOLDER = 'data/parsed_replays/'
TRAIN = DATA_FOLDER + 'train'
VALIDATION = DATA_FOLDER + 'val'
TEST = DATA_FOLDER + 'test'

class PokemonNetworkConfig(object):

	embedding_size = 100
	poke_descriptor_size = 7 # poke id, 4 move ids, item id, status id
	poke_meta_size 1 # current health percentage
	field_meta_size = 0 # number of field status (e.g. weather) -- 0 for now
	number_non_embedding = 12 * poke_meta_size + field_meta_size
	number_classes = 11 # 4 options for each move, +6 options to switch Pokemon, +1 mega-evolve -- ALTERNATIVE, number_moves + number_pokemon + 1 (mega-evolve)
	learning_rate = 1e-3
	max_epochs = 10
	early_stop = 2
	dropout = 0.9
	batch_size = 64
	conv_output_size = 300
	hidden_size = 300
	rnn_layers = 2
	number_pokemon = 0 # TODO 
	number_moves = 0 # TODO 
	number_items = 0 # TODO 
	number_status = 0 # TODO 
	kernels=[1,2,3,4,5,6,7]
	feature_maps=[50,60,70,80,90,100,110,120]

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
			self.embedding_inputs = [tf.nn.embedding_lookup([poke_embeddings,move_embeddings,item_embeddings,status_embeddings],
				placeholder) for placeholder in self.poke_placeholders] 

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
		
		with tf.variable_scope('PokeConvNet'):
			# Conv net layer that uses kernels of different widths to get average representations
			layers = [[] for _ in self.embedding_inputs]
			for idx,kernel_height in enumerate(kernels):
				conv_filter = tf.get_variable('kernel_height:' + str(kernel_height), 
												[kernel_height,self.config.embedding_size,1,self.config.feature_maps[idx]])
				conv_layers = [tf.nn.conv2d(embedding_input,conv_filter,strides=[1,1,1,1],padding='VALID')]
				new_height = self.config.poke_descriptor_size - kernel_height + 1
				pools = [tf.nn.max_pool(tf.tanh(conv), [1,new_height,1,1], [1,1,1,1], 'VALID') for conv in conv_layers]
				layers = [layer.append(tf.squeeze(pool)) for layer,pool in zip(layers,pools)]
			conv_outputs = [tf.concat(layer,1) for layer in layers] # each output is of size [None,sum(feature_maps)]
		with tf.variable_scope('OwnTeamConvNet'):
			own_player_conv = conv_outputs[:6]
			pass 
		with tf.variable_scope('OppTeamConvNet'):
			opp_player_conv = conv_outputs[6:]
			pass 
		with tf.variable_scope('HighwayNet'):
			pass 
		with tf.variable_scope('MemoryLayer'): # uses an LSTM to remember previous moves
			pass 
		with tf.variable_scope('OutputDropout'): # LSTM with OutputProjectionWrapper
			pass 

	def _add_loss(self):
		pass 

	def _add_optimizer(self): 
		pass 

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

