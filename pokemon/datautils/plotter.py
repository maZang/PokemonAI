import numpy as np
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from datautils.const import *

def plot(embeddings):
	'''
	Uses PCA on embeddings to 2D, and then plots the points with their Pokemon labels.
	'''
	pca = PCA(n_components=2)
	X = pca.fit_transform(embeddings)

	BATCH_SIZE = 50

	print(X.shape)

	# y is 700x2
	n, d = X.shape

	x = X[:,0]
	y = X[:,1]

	x1 = x[:BATCH_SIZE]
	y1 = y[:BATCH_SIZE]
	fig1, ax1 = plt.subplots()
	ax1.scatter(x1,y1)

	for i in range(0, BATCH_SIZE):
		ax1.annotate(REV_POKEMON_LIST[i], (x1[i],y1[i]))


	x2 = x[NUMBER_POKEMON:NUMBER_POKEMON+BATCH_SIZE]
	y2 = y[NUMBER_POKEMON:NUMBER_POKEMON+BATCH_SIZE]
	fig2, ax2 = plt.subplots()
	ax2.scatter(x2,y2)

	for i in range(0, BATCH_SIZE):
		ax2.annotate(REV_MOVE_LIST[i+NUMBER_POKEMON], (x2[i],y2[i]))

	x3 = x[NUMBER_POKEMON+NUMBER_MOVES:NUMBER_POKEMON+NUMBER_ITEMS+NUMBER_MOVES]
	y3 = y[NUMBER_POKEMON+NUMBER_MOVES:NUMBER_POKEMON+NUMBER_ITEMS+NUMBER_MOVES]
	fig3, ax3 = plt.subplots()
	ax3.scatter(x3,y3)

	for i in range(0, NUMBER_ITEMS):
		ax3.annotate(REV_ITEM_LIST[i+NUMBER_POKEMON+NUMBER_MOVES], (x3[i],y3[i]))

	plt.show()