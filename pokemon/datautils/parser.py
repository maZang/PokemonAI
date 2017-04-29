import re
import json
from pprint import pprint
import numpy as np
import const
import pickle

BATTLEFILE = 'battlefactory-566090815.txt'
DATAFOLDER = 'data/replays/'
PARSED_FOLDER = 'data/parsed_replays/'
FACTORYSETS = 'data/factory-sets.json'

def encode(network_config, replay_file):
	encoding = PokemonShowdownEncoding.load(replay_file)
	return [encoding.pokemon + [encoding.other_data, encoding.labels]]


class PokemonShowdownEncoding(object):

	def __init__(self, name, num_turns, type):
		'''
		type is either test,train,or val
		'''
		self.name = name
		self.type = type
		self.pokemon = [np.zeros((num_turns, const.POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.other_data = np.zeros((num_turns, const.NON_EMBEDDING_DATA))
		self.labels = np.zeros((num_turns, const.NUMBER_CLASSES))

	@classmethod
	def load(self, filename):
		with open(filename, 'rb') as f:
			pickle.load(f)

	def save(self):
		with open(PARSED_FOLDER + self.type + '/' + self.name + '.p', 'wb') as f:
			pickle.dump(self, f)

class PokemonShowdownReplayParser(object):
	def __init__(self, log=""):
		self.log = log
		self.players = {}
		self.players["p1"] = Player("p1")
		self.players["p2"] = Player("p2")
		self.turnNumber = 0
		self.turnList = {0: []}

	def run(self):
		self.parse()

		self.stripGenders()

		self.parseJSON()

		output = ""
		output += self.players["p1"].getTeamFormatString()
		output += self.players["p2"].getTeamFormatString()
		for item in self.turnList.iteritems():
			print(item)
		return output

	def parse(self):
		''' 
		Parses the log file line by line.
		'''
		lines = self.log.split('\n')
		for line in lines:
			if line.startswith("|player|"):
				self.processPlayer(line)
			elif line.startswith("|poke|"):
				self.processPoke(line)
			elif line.startswith("|win|"):
				self.processWinner(line)
			elif line.startswith("|turn|"):
				self.processTurn(line)
			elif line.startswith("|move|"):
				self.processMove(line)
			elif line.startswith("|-ability|"):
				self.processAbility(line)
			elif line.startswith("|switch|"):
				self.processSwitch(line)
			# elif line.startswith("|drag|"):
			# 	self.processDrag(line)
			elif line.startswith("|-mega|"):
				self.processMega(line)
			elif line.startswith("|detailschange|"):
				self.processDetailsChange(line)
			# elif line.startswith("|-item|"):
			#
			#		self.processItem(line)
			#
			elif line.startswith("|-enditem|"):
				self.processEndItem(line)
			elif "|[from] move:" in line:
				if line.startswith("|-item|"):
					self.processItemFromMove(line)
			elif "|[from] item:" in line:
				if line.startswith("|-heal|"):
					self.processHealFromItem(line)
			elif "[from] ability: " in line:
				if line.startswith("|-weather|"):
					self.processWeatherFromAbility(line)
			else:
				if (line.startswith("|J|")
					or line.startswith("|j|")
					or line.startswith("|L|")
					or line.startswith("|l|")
					or line.startswith("|inactive|")
					or line.startswith("|choice|")
					or line.startswith("|seed|")
					or line.startswith("|rated")
					or line.startswith("|upkeep")
					or line.startswith("|-resisted|")
					or line.startswith("|gametype|")
					or line.startswith("|gen|")
					or line.startswith("|tier|")
					or line.startswith("|-miss|")
					or line.startswith("|clearpoke")
					or line.startswith("|teampreview")
					or line.startswith("|c|")
					or line.startswith("|rule|")
					or line.startswith("|-sidestart|")
					or line.startswith("|-start|")
					or line.startswith("|-damage|")
					or line.startswith("|-fail|")
					or line.startswith("|-activate|")
					or line.startswith("|-boost|")
					or line.startswith("|start")
					or line.startswith("|faint|")
					or line.startswith("|-supereffective|")
					or line.startswith("|-crit|")
					or line.startswith("|-end|")
					or line.startswith("|-singleturn|")
					or line.startswith("|-message|")
					or line.startswith("|cant|")
					or line.startswith("|-status|")
					or line.startswith("|-unboost|")
					or line == "|"):
					pass
				else:
					print(line)

	def parseJSON(self):
		'''
		Parses the factory sets JSON file to fill in all the missing information.
		'''
		with open(FACTORYSETS) as f:
			data = json.load(f)

		for pokemon in self.players["p1"].pokemon:
			self.parsePokemonWithJSON(pokemon, data)
		for pokemon in self.players["p2"].pokemon:
			self.parsePokemonWithJSON(pokemon, data)

	def parsePokemonWithJSON(self, pokemon, data):
		'''
		Parses a pokemon using Battle Factory JSON data.

		Inputs:
		Pokemon - The pokemon to be filled in.
		Data - The Battle Factory JSON data object.
		'''
		# Takes only the beginning part if pokemon is Mega
		if "-Mega" in pokemon.species:
			speciesKey = pokemon.species.split("-")[0]
		# Removes dash
		elif "-" in pokemon.species:
			speciesKey = pokemon.species.replace("-", "")
		else:
			speciesKey = pokemon.species
		speciesKey = speciesKey.lower()

		if speciesKey in data["Uber"]:
			self.fillInPokemon(pokemon, data["Uber"][speciesKey])
		elif speciesKey in data["OU"]:
			self.fillInPokemon(pokemon, data["OU"][speciesKey])
		elif speciesKey in data["UU"]:
			self.fillInPokemon(pokemon, data["UU"][speciesKey])
		elif speciesKey in data["RU"]:
			self.fillInPokemon(pokemon, data["RU"][speciesKey])
		elif speciesKey in data["NU"]:
			self.fillInPokemon(pokemon, data["NU"][speciesKey])
		elif speciesKey in data["PU"]:
			self.fillInPokemon(pokemon, data["PU"][speciesKey])
		else:
			raise Exception("Pokemon not found in JSON!")

	def fillInPokemon(self, pokemon, data):
		'''
		Fills in pokemon based on set from Battle Factory JSON.

		Inputs:
		Pokemon - The pokemon to be filled in.
		Data - The JSON pokemon sub-object with tier and species key already specified, ex. data["Uber"]["klefki"]
		'''
		for pokeSet in data["sets"]:
			validSet = True

			setMoves = pokeSet["moves"]
			setAbility = pokeSet["ability"]
			setItem = pokeSet["item"]
			setSpecies = pokeSet["species"]

			# This usually means pokemon is mega evolved and set is not, or vice versa.
			if pokemon.species != setSpecies:
				print("Pokemon species: " + pokemon.species)
				print("Set species: " + setSpecies)
				pass

			# This means the held item is different from the set item.
			if pokemon.item != None and pokemon.item != "" and pokemon.item != setItem:
				print("Pokemon item: " + pokemon.item)
				print("Set item: " + setItem)
				pass

			assert(len(setMoves) == 4)

			# setMoves is a list of a list of strings. One move slot can have 2 possible moves that are chosen randomly.

			flattenedSetMoves = [item for sublist in setMoves for item in sublist]

			for move in pokemon.moves:
				if move not in flattenedSetMoves:
					validSet = False
					pass

			# This is a valid set.
			if validSet == True:
				finalSet = pokeSet
				break

		assert(finalSet != None)

		pokemon.ability = finalSet["ability"]
		pokemon.item = finalSet["item"]

		for moveSlot in finalSet["moves"]:
			for move in moveSlot:
				if move in pokemon.moves:
					pass
				else:
					pokemon.moves.add(move)
				if len(pokemon.moves) == 4:
					break
			if len(pokemon.moves) == 4:
				break


	def processPlayer(self, line):
		fields = line.split("|")

		if len(fields) >= 4:
			self.players[fields[2]].username = fields[3]


	def processPoke(self, line):
		fields = line.split("|")

		pokemon = Pokemon()
		pokemon.species = fields[3].replace("/,.*$/", "")
		print("Pokemon species: " + pokemon.species)
		self.players[fields[2]].pokemon.append(pokemon)

	def processWinner(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# Assigns username of winner
		winnerUsername = fields[2]
		print("Winner username: " + winnerUsername)

		# TODO: Swap everything here based on winner username

	def processTurn(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# New turn, create a new turn list
		self.turnNumber = int(fields[-1])
		self.turnList[self.turnNumber] = []

	def processSwitch(self, line):
		matches = re.search("\|switch\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		pokemon = self.players[player].getPokemonBySpecies(species)
		if pokemon == None:
			pokemon = Pokemon()
			pokemon.nickname = nickname
			pokemon.species = species
			self.players[player].pokemon.append(pokemon)
			assert(len(self.players[player].pokemon) <= 6)
		elif pokemon.nickname == "":
			pokemon.nickname = nickname
		self.players[player].currentPokemon = pokemon

		# Append to turn object list
		turn = Turn(turnNumber=self.turnNumber, player=player, action="switch", pokemon=pokemon)
		self.turnList[self.turnNumber].append(turn)

	def processMove(self, line):
		matches = re.search("\|move\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		move = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.moves.add(move)
		assert(len(pokemon.moves) <= 4)

		# Append to turn object list
		turn = Turn(turnNumber=self.turnNumber, player=player, action=move, pokemon=pokemon)
		self.turnList[self.turnNumber].append(turn)

	def processAbility(self, line):
		matches = re.search("\|-ability\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		ability = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.ability = ability


	def processMega(self, line):
		matches = re.search("\|-mega\|(p[12])a:\s+([^|]+)\|([^|]+)\|(.+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		# species = matches[2]
		megastone = matches[3]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.item = megastone

		# Append to turn object list
		turn = Turn(turnNumber=self.turnNumber, player=player, action="mega", pokemon=pokemon)
		self.turnList[self.turnNumber].append(turn)

	def processDetailsChange(self, line):
		matches = re.search("\|detailschange\|(p[12])a:\s+([^|]+)\|([^\n]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.species = species
		print("Species: " + pokemon.species)


	def processItemFromMove(self, line):
		matches = re.search("\|-item\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2]

		otherPlayer = "p2" if player == "p1" else "p1"
		otherPokemon = self.players[otherPlayer].currentPokemon

		if otherPokemon.item == "":
			otherPokemon.item = item


	def processEndItem(self, line):
		matches = re.search("\|-enditem\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		if pokemon.item == "":
			pokemon.item = item


	def processHealFromItem(self, line):
		matches = re.search("-heal\|(p[12])a:\s+([^|]+)\|[^|]+\|\[from\] item: (.+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.item = item


	def processWeatherFromAbility(self, line):
		matches = re.search("\|-weather\|[^|]+\|\[from\] ability: ([^|]+)\|\[of\] (p[12])a: (.+)", line).groups()
		ability = matches[0]
		player = matches[1]
		nickname = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.ability = ability

	def stripGenders(self):
		p1 = self.players["p1"]
		p2 = self.players["p2"]

		for poke in p1.pokemon:
			if ',' in poke.species:
				poke.species = poke.species.split(',')[0]

		for poke in p2.pokemon:
			if ',' in poke.species:
				poke.species = poke.species.split(',')[0]


class Player(object):
	def __init__(self, name="", username="", currentPokemon=None):
		self.name = name
		self.username = username
		self.pokemon = []
		self.currentPokemon = currentPokemon

	def getPokemonBySpecies(self, species):
		for poke in self.pokemon:
			if poke.species == species:
				return poke
		return None


	def getPokemonByNickname(self, nickname):
		for poke in self.pokemon:
			if poke.nickname == nickname:
				return poke
		return None


	def getTeamFormatString(self):
		output = "-------------------------\n"
		output += "Player: "+self.username+"\n"
		output += "-------------------------\n"
		for i in range(len(self.pokemon)):
			output += self.pokemon[i].getTeamFormatString() + "\n"
		return output


class Pokemon(object):
	def __init__(self, species="", nickname="", item="", ability=""):
		self.species = species
		self.nickname = nickname
		self.item = item
		self.ability = ability
		self.moves = set()

	def __repr__(self):
		return "(Pokemon: (species={}, nickname={}, item={}, ability={}))".format(self.species, self.nickname, self.item, self.ability)

	def getTeamFormatString(self):
		s = ""
		s += self.species + " @ " + self.item +"\n"
		s += "Ability: "+ self.ability + "\n"
		for move in self.moves:
			s += "- " + move + "\n"
		return s


class Turn(object):
	def __init__(self, turnNumber=None, player=None, action=None, pokemon=None, state=None):
		self.turnNumber = turnNumber
		self.player = player
		self.action = action
		self.pokemon = pokemon
		self.state = state

	def __repr__(self):
		return "(Turn {}: (player={}, action={}, pokemon={}, state={})".format(self.turnNumber, self.player, self.action, self.pokemon, self.state)


class FieldState(object):
	def __init__(self, p1Pokemon, p2Pokemon, weather=None):
		self.p1Pokemon = p1Pokemon
		self.p2Pokemon = p2Pokemon
		self.p1EntryHazards = []
		self.p2EntryHazards = []
		self.weather = weather

def main():
	with open(DATAFOLDER + BATTLEFILE) as file:
		data = file.read()

	parser = PokemonShowdownReplayParser(data)
	output = parser.run()
	print(output)

if __name__ == "__main__":
	main()
