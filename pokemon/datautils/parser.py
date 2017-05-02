# -*- coding: utf-8 -*-
import re
import json
import numpy as np
import pickle
import os
import random

from pprint import pprint
from const import *

BATTLEFILE = 'battlefactory-566172293.txt'
DATAFOLDER = 'data/replays/'
PARSED_FOLDER = 'data/parsed_replays/'
FACTORYSETS = 'data/factory-sets.json'


def encode(network_config, replay_file):
	encoding = PokemonShowdownEncoding.load(replay_file)
	return [encoding.pokemon + [encoding.other_data, encoding.labels]]


def getActionIDFromString(actionString, pokemon=None):
	# actionID is either a Pokemon actionID if that pokemon switched in
	# Move actionID if they used that move, or -1 if mega evolve
	if actionString in ['switch', 'mega']:
		actionID = POKEMON_LIST[pokemon]
	else:
		# ??????????
		if actionString == 'Hidden Power':
			actionID = MOVE_LIST['<UNK>']
		else:
			actionID = MOVE_LIST[actionString]

	return actionID


class PokemonShowdownEncoding(object):
	def __init__(self, name=None, data_type=None, num_turns=None):
		'''
		data_type is either test,train,or val
		'''
		self.name = name
		self.data_type = data_type
		self.num_turns = num_turns
		self.pokemon = [np.zeros((self.num_turns, POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.other_data = np.zeros((self.num_turns, NON_EMBEDDING_DATA))
		self.labels = np.zeros((self.num_turns, NUMBER_CLASSES))

		# Matrix where row = turn number, column 0 = winner's last move,
		# column 1 = opponent's last move
		self.last_move_data = np.zeros((self.num_turns, 2))

	@classmethod
	def load(self, filename):
		with open(filename, 'rb') as f:
			pickle.load(f)

	def save(self):
		with open(PARSED_FOLDER + self.type + '/' + self.name + '.p', 'wb') as f:
			pickle.dump(self, f)

	def encodePokemonObject(self, pokemon):
		'''
		Encodes a pokemon object. Fills in any unknown moves/items with an unknown token.

		Input: Pokemon object
		Output: Pokemon encoding object with shape (1, POKE_DESCRIPTOR_SIZE)
		'''
		pokemon_encoding = np.zeros((1, POKE_DESCRIPTOR_SIZE))

		pokemon_id = POKEMON_LIST[pokemon.species]

		move_ids = []

		# Encodes pokemon item
		if pokemon.item in ITEM_LIST:
			item_id = ITEM_LIST[pokemon.item]
		else:
			item_id = ITEM_LIST['<UNK>']

		for move in pokemon.moves:
			if move in MOVE_LIST:
				move_ids.append(MOVE_LIST[move])
			else:
				move_ids.append(MOVE_LIST['<UNK>'])

		if len(move_ids) < 4:
			num_unk_moves = 4 - len(move_ids)
			for i in range(num_unk_moves):
				move_ids.append(MOVE_LIST['<UNK>'])

		assert(len(move_ids) == 4)

		if pokemon.status == "psn":
			status_key = "POISONED"
		elif pokemon.status == "tox":
			status_key = "BADLY_POISONED"
		elif pokemon.status == "brn":
			status_key = "BURNED"
		elif pokemon.status == "par":
			status_key = "PARALYZED"
		elif pokemon.status == "slp":
			status_key = "SLEEP"
		elif pokemon.status == "frz":
			status_key = "FROZEN"
		else:
			status_key = "NONE"

		status_id = STATUS_IDS[status_key]

		pokemon_encoding[:, 0] = pokemon_id
		for i in range(len(move_ids)):
			pokemon_encoding[:, i+1] = move_ids[i]
		pokemon_encoding[:, 5] = item_id
		pokemon_encoding[:, 6] = status_id

		return pokemon_encoding

	def encodeLabels(self, turnList, winner):
		for turnNumber, lst in turnList.iteritems():
			if len(lst) > 2:
				raise Exception("List {} has more than 2 actions".format(lst))

			for turn in lst:
				if turn.player != winner:
					raise Exception("This should literally never raise.")

				actionID = getActionIDFromString(turn.action, pokemon=turn.pokemon.species)
				col = 0 if turn.player == winner else 1
				self.last_move_data[turnNumber][col] = actionID

				self.labels[turnNumber][actionID] = 1

		# if any(sum(row) != 1 for row in self.labels):
		for i, row in enumerate(self.labels):
			if sum(row) != 1:
				print(i)
				print(row)
				raise Exception("Labels {} had a non-one row".format(self.labels))

	# This code is so jank I never want to look at it again
	def encodeOpponentsLastMove(self, opponentTurnList):
		if len(opponentTurnList) <= 1:
			return

		index = 0
		turnNumbers = opponentTurnList.keys()
		nextTurnNumber = turnNumbers[index+1]
		for turnNumber, lst in opponentTurnList.iteritems():
			# Only care about the last move in sequence of multiple moves
			actionID = getActionIDFromString(lst[-1].action, pokemon=lst[-1].pokemon.species)
			print(turnNumber, nextTurnNumber)
			for x in range(turnNumber, nextTurnNumber):
				self.last_move_data[x][1] = actionID

			if index + 1 == len(opponentTurnList) - 1:
				nextTurnNumber = self.num_turns
			else:
				index += 1
				nextTurnNumber = turnNumbers[index+1]

		print self.last_move_data


class PokemonShowdownReplayParser(object):
	def __init__(self, log="", winner=""):
		self.log = log
		self.players = {}
		self.players["p1"] = Player("p1")
		self.players["p2"] = Player("p2")

		# self.winner is either "p1" or "p2".
		self.winner = winner

		self.turnNumber = -1
		self.turnList = {}
		self.opponentTurnList = {}

		self.lines = None

	def run(self):
		self.parse()

		assert(self.winner == "p1" or self.winner == "p2")

		self.stripGenders()
		self.parseJSON()
		print(self.winner)
		for item in self.turnList.iteritems():
			print(item)
		for item in self.opponentTurnList.iteritems():
			print(item)

		self.generateEncodingObject()

		'''
		encoding = PokemonShowdownEncoding()
		for pokemon in self.players["p1"].pokemon:
			print(encoding.encodePokemonObject(pokemon))
		for pokemon in self.players["p2"].pokemon:
			print(encoding.encodePokemonObject(pokemon))
		'''

		'''
		output = ""
		output += self.players["p1"].getTeamFormatString()
		output += self.players["p2"].getTeamFormatString()
		for item in self.turnList.iteritems():
			print(item)


		return output
		'''

	def generateEncodingObject(self):
		# 80-10-10 Training-Validation-Testing Split
		weighted_data_types = [DATA_TYPES[0]] * 8 + [DATA_TYPES[1]] + [DATA_TYPES[2]]
		obj = PokemonShowdownEncoding(name=self.log, data_type=random.choice(weighted_data_types), num_turns=self.turnNumber+1)

		obj.encodeLabels(self.turnList, self.winner)
		obj.encodeOpponentsLastMove(self.opponentTurnList)

		return obj

	def parse(self):
		'''
		Parses the log file line by line.
		'''
		self.lines = self.log.split('\n')

		# First parse the players
		for line in self.lines:
			if line.startswith("|player|"):
				self.processPlayer(line)
				if "|p2|" in line:
					break

		# Then parse the winner
		for line in reversed(self.lines):
			if line.startswith("|win|"):
				self.processWinner(line)
				break

		# Finally parse the rest of the lines
		for i, line in enumerate(self.lines):
			if line.startswith("|poke|"):
				self.processPoke(line)
			elif line.startswith("|turn|"):
				self.processTurn(line)
			elif line.startswith("|move|"):
				self.processMove(line)
			elif line.startswith("|-ability|"):
				self.processAbility(line)
			elif line.startswith("|switch|"):
				self.processSwitch(line)
			elif line.startswith("|drag|"):
			 	self.processDrag(line)
			elif line.startswith("|-mega|"):
				self.processMega(line)
			elif line.startswith("|detailschange|"):
				self.processDetailsChange(line)
			elif line.startswith("|replace|"):
				self.processReplace(line)
			elif line.startswith("|-status|"):
				self.processStatus(line)
			elif line.startswith("|-curestatus|"):
				self.processCureStatus(line)
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
					or line.startswith("|-unboost|")
					or line == "|"):
					pass

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
		else:
			speciesKey = ''.join(e for e in pokemon.species if e.isalnum())
		speciesKey = speciesKey.lower()

		if speciesKey == "groudonprimal":
			speciesKey = "groudon"
		if speciesKey == "kyogreprimal":
			speciesKey = "kyogre"
		if speciesKey == "gourgeist":
			speciesKey = "gourgeistsuper"

		pokeSets = []
		if speciesKey in data["Uber"]:
			pokeSets.extend(data["Uber"][speciesKey]["sets"])
		if speciesKey in data["OU"]:
			pokeSets.extend(data["OU"][speciesKey]["sets"])
		if speciesKey in data["UU"]:
			pokeSets.extend(data["UU"][speciesKey]["sets"])
		if speciesKey in data["RU"]:
			pokeSets.extend(data["RU"][speciesKey]["sets"])
		if speciesKey in data["NU"]:
			pokeSets.extend(data["NU"][speciesKey]["sets"])
		if speciesKey in data["PU"]:
			pokeSets.extend(data["PU"][speciesKey]["sets"])

		if len(pokeSets) == 0:
			raise Exception("Pokemon not found in JSON!")

		self.fillInPokemon(pokemon, pokeSets)

	def fillInPokemon(self, pokemon, pokeSets):
		'''
		Fills in pokemon based on set from Battle Factory JSON.

		Inputs:
		pokemon - The pokemon to be filled in.
		pokeSets - A list of pokemon sets specific to the specified pokemon.
		'''
		finalSet = None

		for pokeSet in pokeSets:
			validSet = True

			setMoves = pokeSet["moves"]
			setAbility = pokeSet["ability"]
			setItem = None
			# In some cases, the pokemon set does not have an item.
			if "item" in pokeSet:
				setItem = pokeSet["item"]
			setSpecies = pokeSet["species"]

			# If pokemon name is "POKENAME-Mega", this slices off the "-Mega"
			if "-Mega" in pokemon.species and pokemon.species.split("-")[0] != setSpecies:
				pass

			# This means the held item is different from the set item.
			if pokemon.item != "" and pokemon.item != setItem:
				pass

			assert(len(setMoves) == 4)

			# Removes "Hidden Power" from pokemon moveset so "Hidden Power [TYPE]" can be added.
			if "Hidden Power" in pokemon.moves:
				pokemon.moves.remove("Hidden Power")

			flattenedSetMoves = [item for sublist in setMoves for item in sublist]

			for move in pokemon.moves:
				if move not in flattenedSetMoves:
					validSet = False
					pass

			# This is a valid set.
			if validSet:
				finalSet = pokeSet
				break

		if finalSet == None:
			print("Species with no matching pokemon set: " + pokemon.species)
			print("Item: " + pokemon.item)
			print("Ability: " + pokemon.ability)
			print(pokemon.moves)
			print("No matching pokemon set!")
			print("Assigning random pokemon set!")
			finalSet = pokeSets[0]

		assert(finalSet != None)

		if pokemon.ability == "":
			pokemon.ability = finalSet["ability"]

		if pokemon.item == "" and "item" in finalSet:
			pokemon.item = finalSet["item"]

		for moveSlot in finalSet["moves"]:
			if len(pokemon.moves) == 4:
				break

			moves = set(moveSlot)

			# The move is already in the pokemon's moves.
			if moves.intersection(pokemon.moves):
				pass
			else:
				pokemon.moves.add(moveSlot[0])

	def processPlayer(self, line):
		fields = line.split("|")

		if len(fields) >= 4:
			self.players[fields[2]].username = fields[3]

	def processPoke(self, line):
		fields = line.split("|")

		pokemon = Pokemon()
		species = fields[3].replace("/,.*$/", "")
		pokemon.species = species
		self.players[fields[2]].pokemon.append(pokemon)

	def processWinner(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# Assigns username of winner
		winnerUsername = fields[2]

		if self.players["p1"].username == winnerUsername:
			self.winner = "p1"
		else:
			self.winner = "p2"

	def processTurn(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# # New turn, create a new turn list
		# self.turnNumber = self.turnNumber + 1
		# self.turnList[self.turnNumber] = []

	def prefixHandler(self, pokePrefix, species, player):
		'''
		Handles prefix edge cases. When pokemon are listed at the top of a battle log,
		their name is "Arceus-*". When they are switched in, they are listed as "Arceus-Ghost".
		This function sets the pokemon species to the specific species.

		Inputs:
		pokePrefix - Pokemon prefix.
		species - Pokemon species.
		player - Player string ("p1" or "p2")
		'''
		pokemon = self.players[player].getPokemonBySpecies(pokePrefix)
		if pokemon == None:
			pokemon = self.players[player].getPokemonBySpecies(pokePrefix + "-*")
		if pokemon == None:
			pokemon = self.players[player].getPokemonBySpecies(pokePrefix + "-*, M")
		if pokemon == None:
			pokemon = self.players[player].getPokemonBySpecies(pokePrefix + "-*, F")

		if pokemon != None:
			pokemon.species = species

	def processSwitch(self, line):
		matches = re.search("\|switch\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		# Special prefix edge case.
		if "Arceus" in species:
			self.prefixHandler("Arceus", species, player)
		elif "Gourgeist" in species:
			self.prefixHandler("Gourgeist", species, player)
		elif "Genesect" in species:
			self.prefixHandler("Genesect", species, player)

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

		# Skip the initial start
		# if "|start" not in [lines[i-1], lines[i-2]]:
		self.createTurn(player, "switch", pokemon)

	def processDrag(self, line):
		matches = re.search("\|drag\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		# Special prefix edge case.
		if "Arceus" in species:
			self.prefixHandler("Arceus", species, player)
		elif "Gourgeist" in species:
			self.prefixHandler("Gourgeist", species, player)
		elif "Genesect" in species:
			self.prefixHandler("Genesect", species, player)

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

	def processReplace(self, line):
		matches = re.search("\|replace\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		# Special prefix edge case.
		if "Arceus" in species:
			self.prefixHandler("Arceus", species, player)
		elif "Gourgeist" in species:
			self.prefixHandler("Gourgeist", species, player)
		elif "Genesect" in species:
			self.prefixHandler("Genesect", species, player)

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

	def processMove(self, line):
		matches = re.search("\|move\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		move = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)

		# This is so that moves from Magic Bounce don't get added to moveset.
		if "[from]" not in line and "Struggle" not in line:
			pokemon.moves.add(move)
		assert(len(pokemon.moves) <= 4)

		self.createTurn(player, move, pokemon)

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

		self.createTurn(player, "mega", pokemon)

	def processDetailsChange(self, line):
		matches = re.search("\|detailschange\|(p[12])a:\s+([^|]+)\|([^\n]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.species = species

	def processStatus(self, line):
		matches = re.search("\|-status\|(p[12])a:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		status = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.status = status
		print(pokemon.status)

	def processCureStatus(self, line):
		matches = re.search("\|-curestatus\|(p[12])a{0,1}:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.status = ""

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
		matches = re.search("\|-heal\|(p[12])a:\s+([^|]+)\|[^|]+\|\[from\] item: (.+)", line).groups()
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

	def createTurn(self, player, action, pokemon):
		# Append to turn object list
		if player == self.winner:
			self.turnNumber = self.turnNumber + 1

		turn = Turn(turnNumber=self.turnNumber, player=player, action=action, pokemon=pokemon)

		if player == self.winner:
			self.turnList[self.turnNumber] = [turn]
		else:
			# Cheesy stuff
			turnNumber = max(0, self.turnNumber)
			if turnNumber in self.opponentTurnList:
				self.opponentTurnList[turnNumber].append(turn)
			else:
				self.opponentTurnList[turnNumber] = [turn]


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
		for pokemon in self.pokemon:
			print(pokemon)
			output += pokemon.getTeamFormatString() + "\n"
		return output


class Pokemon(object):
	def __init__(self, species="", nickname="", item="", ability="", status=""):
		self.species = species
		self.nickname = nickname
		self.item = item
		self.ability = ability
		self.status = status
		self.moves = set()

	def __repr__(self):
		return "(Pokemon: (species={}, nickname={}, item={}, ability={}))".format(self.species, self.nickname, self.item, self.ability)

	def getTeamFormatString(self):
		s = ""
		s += self.species + " @ " + self.item +"\n"
		s += "Ability: " + self.ability + "\n"
		for move in self.moves:
			s += "- " + move + "\n"
		print(s + "\n")
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
	# with open(DATAFOLDER + BATTLEFILE) as file:
		# data = file.read()
	counter = 0
	for filename in os.listdir(DATAFOLDER):
		print("Counter: " + str(counter))
		if filename.endswith(".txt") and "battlefactory" in filename:
			print(filename)
			file = os.path.join(DATAFOLDER, filename)
			data = open(file).read()
			parser = PokemonShowdownReplayParser(data)
			parser.run()
			# print(output)
		counter += 1

if __name__ == "__main__":
	main()
