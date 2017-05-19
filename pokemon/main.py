import sys
import tensorflow as tf

from datautils.plotter import plot
from learner.approxqlearner import AIConfig

#from datautils import replaycrawler as replay
from game.pokemonenv import PokemonShowdownConfigSelfPlay, runPokemonShowdown, runAgainstItself
import learner.superviser.supervisernetwork as supnet
from datautils import parser as parser

def runSupervised():
	supnet.trainNetwork()

def main(args):
	#replay.spiderman()
	#runPokemonShowdown()

	if args[0] in ['y', '1', 'True', 'T', 'Y']:
		arg = True
	else:
		arg = False
	runAgainstItself(isOpponent=arg)

	#replay.crawl()
	#runSupervised()
	#runParser()
	# restoreTFVariables()

def runParser():
	parser.main()

def restoreTFVariables():
	VARIABLE_PATH = "data/models/pokemon_ai"
	USERNAME = "CS6700AITest"

	MODEL_PATH = VARIABLE_PATH + "/" + USERNAME

	config = PokemonShowdownConfigSelfPlay()

	learner = config.learner(None, lambda x: x, config.network, {'buffer_size' : 1000}, AIConfig(), config.user, load_model=True)

	embeddings = learner.sess.run(learner.mainQN.all_embeddings)

	print(embeddings.shape)

	plot(embeddings)

if __name__ == "__main__":
	main(sys.argv[1:])
