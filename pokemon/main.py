import sys

#from datautils import replaycrawler as replay
from game.pokemonenv import runPokemonShowdown, runAgainstItself
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

def runParser():
	parser.main()

if __name__ == "__main__":
	main(sys.argv[1:])
