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
		files = [[os.path.join(sample_folder,f) 
					for f in os.listdir(sample_folder) if os.path.isfile(os.path.join(sample_folder, f))]
					for sample_folder in [train_folder, val_folder, test_folder]]
		sets = [[],[],[]]
		for all_files,set in zip(files,sets):
			for file in all_files:
				set.append(sample_encoder(file))
		self.training = sets[0]
		self.validation = sets[1]
		self.testing = sets[2]

	def number_batches(self, batch_size, num_steps):
		return np.sum([train[-1].shape[0] - num_steps + 1 for train in self.training])

	def get_data(self, type):
		if type=='train':
			data = self.training 
		elif type=='val':
			data = self.validation
		else:
			data = self.testing
		return data

	def get_idxs(self, num_steps, type):
		data = self.get_data(type)
		print(data)
		return np.random.permutation([(i,j) for i in range(len(data)) 
					for j in range(data[i][-1].shape[0] - num_steps + 1)])

	def sample(self, batch_size, num_steps, type='train'):
		'''
		Generator that passes in data until complete # TODO
		'''
		idxs = self.get_idxs(num_steps, type)
		data = self.get_data(type)
		currBatch = 0
		while currBatch < idxs.shape[0]:
			eps,seq = idxs[currBatch]
			yield [set[seq:seq+num_steps] for set in data[eps]]
			currBatch += 1

