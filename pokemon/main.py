#from datautils import replaycrawler as replay
from game.pokemonenv import runPokemonShowdown, runAgainstItself
import learner.superviser.supervisernetwork as supnet
from datautils import parser as parser

def runSupervised():
	supnet.trainNetwork()

def main():
	#replay.spiderman()
	#runPokemonShowdown()
	runAgainstItself()
	#replay.crawl()
	#runSupervised()
	#runParser()

def runParser():
	parser.main()

if __name__ == "__main__":
	main()

