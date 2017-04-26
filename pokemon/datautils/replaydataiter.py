import numpy as np 

class ReplayDataIter(object):

	def __init__(self):
		self.samples = []
		self.num_samples = 0