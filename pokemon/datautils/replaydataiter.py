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
		return math.ceil(np.sum([train[-1].shape[0] - num_steps + 1 for train in self.training]) / batch_size)

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
		return np.random.permutation([(i,j) for i in range(len(data))
					for j in range(data[i][-1].shape[0] - num_steps + 1)])

	def sample(self, batch_size, num_steps, type='train'):
		'''
		Generator that passes in data until complete # TODO
		'''
		idxs = self.get_idxs(num_steps, type)
		number_batches = self.number_batches(batch_size, num_steps)
		data = self.get_data(type)
		currBatch = 0
		while currBatch < number_batches:
			all_sets = [[] for _ in range(len(data[0]))]
			for eps,seq in idxs[currBatch*batch_size:(currBatch+1)*batch_size]:
				[all_sets_set.append(set[seq:seq+num_steps]) for set,all_sets_set in zip(data[eps],all_sets)]
			try:
				final_batch = [np.concatenate(sets, axis=0) for sets in all_sets]
			except:
				# print(len(idxs))
				# print(currBatch)
				# print(number_batches)
				# for eps,seq in idxs[currBatch*batch_size:(currBatch+1)*batch_size]:
				# 	print(eps)
				# 	print(seq)
				# 	for set,all_sets_set in zip(data[eps],all_sets):
				# 		print(set)
				# 		print(all_sets_set)
				# print("HMM")
				raise
			final_batch[-1] = np.where(final_batch[-1] == 1)[1] # quick hack
			yield final_batch
			currBatch += 1

