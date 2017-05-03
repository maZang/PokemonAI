from datautils import replaycrawler as replay 
from game.pokemonenv import runPokemonShowdown, runAgainstItself
import learner.superviser.supervisernetwork as supnet
from datautils import parser as parser 

def runSupervised():
	supnet.trainNetwork()

def main():
	replay.bulk_search()
	#runPokemonShowdown()
	#runAgainstItself()
	#replay.crawl()

def runParser():
	parser.main()

if __name__ == "__main__":
	main()

