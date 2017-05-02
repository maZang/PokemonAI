from datautils import replaycrawler as replay 
from game.pokemonenv import runPokemonShowdown, runAgainstItself
import learner.superviser.supervisernetwork as supnet

def runSupervised():
	supnet.trainNetwork()

def main():
	replay.spiderman()
	#runPokemonShowdown()
	#runAgainstItself()
	#replay.crawl()

if __name__ == "__main__":
	main()

