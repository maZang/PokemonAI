import numpy as np 

def euclid(X, Z):
	return np.array(np.matrix(np.sum(X * X, axis=1)).T - 2 * X.dot(Z.T) + np.sum(Z * Z, axis=1))

def kmeans(points, centroids):
	print('Points')
	print(points)
	cluster = np.array([-1] * points.shape[0])
	while True:
		dists = euclid(points, centroids)
		next_cluster = np.argmin(dists, axis=1)
		print('\tCurrent Centroids')
		print(centroids)
		print('\tDistances')
		print(dists)
		print('\tClusters')
		print(next_cluster)
		if np.all(cluster == next_cluster):
			break 
		cluster = next_cluster
		centroids = np.array([np.mean(points[cluster == i], axis=0) for i in range(centroids.shape[0])])

points = np.array([[0,0],[0,1],[1,0],[2,3],[3,2],[3,3]])
centroids = np.array([[2,3],[3,3]])
kmeans(points, centroids)
