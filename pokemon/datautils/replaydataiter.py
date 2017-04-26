import numpy as np 
import os
import math 

class ReplayDataIter(object):

	def __init__(self, train_folder, val_folder, test_folder, sample_encoder):
		'''
		Sample encodings are of the form 
		[Poke1,Move1,Move2,Move3,Move4,HP,Status] * 6 for all Player Pokes
		[Poke1,Move1,Move2,Move3,Move4,HP,Status] * 6 for all Opponent Pokes 
		for now, some field state as well
		[Rain, Sun, Sandstorm, etc...]
		'''
		self.samples = []
		files = [[f for f in os.listdir(sample_folder) if os.path.isfile(os.path.join(sample_folder, f))]
					for sample_folder in [train_folder, val_folder, test_folder]]
		def load_data(all_files, samples):
			for file in all_files:
				samples.extend(sample_encoder(file))
		sets = [[],[],[]]
		map(zip(files,sets), lambda x: load_data(x[0], x[1]))
		self.training = np.array(sets[0])
		self.validation = np.array(sets[1])
		self.testing = np.array(sets[2])

	def sample(self, batch_size):
		'''
		Generator that passes in data until complete
		'''
		trainData = np.random.permutation(self.training)
		numBatches = math.ceil(trainData.shape[0] / batch_size)
		currBatch = 0
		while currBatch < numBatches:
			yield trainData[currBatch * batch_size : (currBatch + 1) * batch_size, :]
			currBatch += 1

