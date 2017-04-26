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
	x_number_embedding = 12 * poke_descriptor_size
	x_number_other = 12 * poke_meta_size + field_meta_size
	number_classes = 10 # 4 options for each move, +6 options to switch Pokemon
	learning_rate = 1e-3
	max_epochs = 10
	early_stop = 2
	dropout = 0.9
	batch_size = 64
	conv_output_size = 300
	hidden_size = 300
	number_pokemon = 0 # TODO 
	number_moves = 0 # TODO 
	number_items = 0 # TODO 
	number_status = 0 # TODO 

class PokemonNetwork(object):

	def _add_placeholder(self):
		self.x_embedding_placeholder = tf.placeholder(tf.float32, shape=(None, x_number_embedding))
		self.x_data_placeholder = tf.placeholder(tf.float32, shape=(None, x_number_other))
		self.y_placeholder = tf.placeholder(tf.float32, shape=(None, number_classes))
		self.dropout_placeholder = tf.placeholder(tf.float32)

	def _add_embedding(self):
		'''
		Extracts the embeddings out of the current vector
		Assumes the encoding is like
		[Poke1, Move1, Move2, Move3, Move4, Item1, Status1] * 12 + [Poke1Hp] * 12
		Note, ids are shared between pokemon, moves, items, and statuses -- ENSURE THIS IN ENCODING

		Final output is of shape
			 [None, x_number_embedding, embedding_size] 
		which is 
			 [batch_size, num_steps, x_number_embedding, embedding_size] 
		'''
		with tf.device('/cpu:0'):
			poke_embeddings = tf.get_variable('poke_embeddings', shape=(self.config.number_pokemon, self.config.embedding_size))
			move_embeddings = tf.get_variable('move_embeddings', shape=(self.config.number_moves, self.config.embedding_size))
			item_embeddings = tf.get_variable('item_embeddings', shape=(self.config.number_items, self.config.embedding_size))
			status_embeddings = tf.get_variable('status_embeddings', shape=(self.config.number_status, self.config.embedding_size))
			self.embedding_inputs = tf.nn.embedding_lookup([poke_embeddings,move_embeddings,item_embeddings,status_embeddings],
				self.x_embedding_placeholder) 

	def _network_model(self):
		'''
		Applies all the conv layers to retrive a final Memory layer of shape
		[batch_size, number_steps, hidden_size]
		'''
		with tf.variable_scope('InputDropout'):
			pass 
		with tf.variable_scope('PokeConvNet'):
			pass 
		with tf.variable_scope('OwnTeamConvNet')
			pass 
		with tf.variable_scope('OppTeamConvNet'):
			pass 
		with tf.variable_scope('MemoryLayer'): # uses an LSTM to remember previous moves
			pass 
		with tf.variable_scope('OutputDropout'): # LSTM with OutputProjectionWrapper
			pass 

	def _add_scores(self):
		pass 

	def _add_loss(self):
		pass 

	def _add_optimizer(self): 
		pass 

	def _build_graph(self):
		self._add_placeholder()
		self._add_embedding()
		self._network_model()
		self._add_scores()
		self._add_loss()
		self._add_optimizer()

	def __init__(self, config):
		self.data_iter = ReplayDataIter(TRAIN, VALIDATION, TEST, lambda x: encode(config, x))
		self.config = config
		self._build_graph()

