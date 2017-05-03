# -*- coding: utf-8 -*-
import re
import json
import pickle
import os
import random

from const import *
from encoding import *
from player import *
from pokemon import *
from turn import *

BATTLEFILE = 'battlefactory-566258957.txt'
DATAFOLDER = 'data/replays/'
PARSED_FOLDER = 'data/parsed_replays/'
FACTORYSETS = 'data/factory-sets.json'

class PokemonShowdownReplayParser(object):
	def __init__(self, log=""):
		self.log = log
		self.players = {}
		self.players["p1"] = Player("p1")
		self.players["p2"] = Player("p2")

		# self.winner is either "p1" or "p2".
		self.winner = None
		self.opponent = None

		self.turnNumber = -1
		self.turnList = {}
		self.opponentTurnList = {}
		self.pokemonEncoding = {}

		self.lines = None

		self.simulate = False

	def run(self):
		'''
		First parses through the log file to fill in pokemon sets.
		Then parses through the log file again to simulate the battle.
		'''

		# Parse through the log file and fill in any seen abilities, items, or moves.
		self.parse()

		assert(self.winner == "p1" or self.winner == "p2")
		assert(self.opponent == "p1" or self.opponent == "p2" and self.opponent != self.winner)

		# Parse through the JSON file and fill in pokemon sets.
		self.parseJSON()


		# Simulate through the battle and generate pokemon and state encodings for each turn.
		self.simulate = True
		self.players[self.opponent].resetPokemon()
		self.players[self.winner].resetStatuses()
		self.players[self.winner].resetMega()

		self.parse()

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
		obj.encodePokemon(self.pokemonEncoding)

		# for turnNumber, lst in self.pokemonEncoding.items():
			# print lst[0]

		return obj

	def parse(self):
		'''
		Parses the log file line by line.
		'''
		self.lines = self.log.split('\n')

		for line in self.lines:
			if line.startswith("|player|"):
				self.processPlayer(line)
			elif line.startswith("|poke|"):
				self.processPoke(line)
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
			elif line.startswith("|win|"):
				self.processWinner(line)
			elif line.startswith("|-status|"):
				self.processStatus(line)
			elif line.startswith("|-curestatus|"):
				self.processCureStatus(line)
			elif line.startswith("|-damage|"):
				self.processDamage(line)
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
					self.processHeal(line)
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

	def processPlayer(self, line):
		fields = line.split("|")

		if not self.simulate and len(fields) >= 4:
			self.players[fields[2]].username = fields[3]

	def processPoke(self, line):
		fields = line.split("|")
		player = fields[2]
		species = fields[3].replace("/,.*$/", "").split(',')[0]

		if "Arceus" in species:
			species = "Arceus"
		elif "Gourgeist" in species:
			species = "Gourgeist"
		elif "Genesect" in species:
			species = "Genesect"

		if not self.simulate:
			pokemon = Pokemon()
			pokemon.species = species
			self.players[player].pokemon.append(pokemon)

	def processWinner(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# Assigns username of winner
		winnerUsername = fields[2]

		if self.players["p1"].username == winnerUsername:
			self.winner = "p1"
			self.opponent = "p2"
		else:
			self.winner = "p2"
			self.opponent = "p1"

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

		if pokemon != None:
			pokemon.species = species

	def processSwitch(self, line):
		matches = re.search("\|switch\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

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

		# Encode winner and opponent player states as well as turn information.
		if self.simulate:
			# Skip the initial start
			# if "|start" not in [lines[i-1], lines[i-2]]:
			self.createTurn(player, "switch", pokemon)

	def processDrag(self, line):
		matches = re.search("\|drag\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		# Special prefix edge case.
		if "Arceus" in species:
			self.prefixHandler("Arceus", species, player)
		elif "Gourgeist" in species:
			self.prefixHandler("Gourgeist", species, player)
		elif "Genesect" in species:
			self.prefixHandler("Genesect", species, player)

		pokemon = self.players[player].getPokemonBySpecies(species)

		# When pokemon has not mega-evolved yet, but the pokemon in the players inventory is -Mega.
		'''
		if self.simulate and player == self.winner:
			if not pokemon:
				pokemon = self.players[player].getPokemonByNickname(nickname)
				pokemon.species = species
		'''

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
		species = matches[2].split(',')[0]

		# Special prefix edge case.
		if "Arceus" in species:
			self.prefixHandler("Arceus", species, player)
		elif "Gourgeist" in species:
			self.prefixHandler("Gourgeist", species, player)
		elif "Genesect" in species:
			self.prefixHandler("Genesect", species, player)

		pokemon = self.players[player].getPokemonBySpecies(species)

		# When pokemon has not mega-evolved yet, but the pokemon in the players inventory is -Mega.
		'''
		if self.simulate and player == self.winner:
			if not pokemon:
				pokemon = self.players[player].getPokemonByNickname(nickname)
				pokemon.species = species
		'''

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

		if self.simulate:
			if player == self.opponent:
				# This is so that moves from Magic Bounce don't get added to moveset.
				if "[from]" not in line and "Struggle" not in line:
					pokemon.moves.add(move)
		else:
			# This is so that moves from Magic Bounce don't get added to moveset.
			if "[from]" not in line and "Struggle" not in line:
				pokemon.moves.add(move)

		assert(len(pokemon.moves) <= 4)

		# Encode winner and opponent player states as well as turn information.
		if self.simulate:
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

		# Encode winner and opponent player states as well as turn information.
		if self.simulate:
			self.createTurn(player, "mega", pokemon)

	def processDetailsChange(self, line):
		matches = re.search("\|detailschange\|(p[12])a:\s+([^|]+)\|([^\n]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.species = species

	def processStatus(self, line):
		matches = re.search("\|-status\|(p[12])a:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		status = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.status = status

	def processCureStatus(self, line):
		matches = re.search("\|-curestatus\|(p[12])a{0,1}:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.status = ""

	def processDamage(self, line):
		matches = re.search("\|-damage\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		health = matches[2].split('/')[0]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.health = health

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

	def processHeal(self, line):
		matches = re.search("\|-heal\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		health = matches[2].split('/')[0]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.health = health


	def processWeatherFromAbility(self, line):
		matches = re.search("\|-weather\|[^|]+\|\[from\] ability: ([^|]+)\|\[of\] (p[12])a: (.+)", line).groups()
		ability = matches[0]
		player = matches[1]
		nickname = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.ability = ability

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

		turnNm = max(0, self.turnNumber)
		self.pokemonEncoding[turnNm] = [encodePokemonObject(Pokemon())]*12

		self.encodePokemon(turnNm, "p1")
		self.encodePokemon(turnNm, "p2")

	def encodePokemon(self, turnNumber, player):
		playerPokemon = self.players[player]
		currentPokemon = self.players[player].currentPokemon
		if not currentPokemon:
			return

		idx = 0
		if player != self.winner:
			idx = 6

		# 0-5 = Winner's pokemon, 6-11 = Opponent's pokemon
		# Turn number : list of 12 pokemon that represents
		self.pokemonEncoding[turnNumber][idx] = encodePokemonObject(currentPokemon)

		i = 1
		for pokemon in playerPokemon.pokemon:
			if pokemon == currentPokemon:
				continue
			self.pokemonEncoding[turnNumber][i+idx] = encodePokemonObject(pokemon)
			i += 1

def main():
	'''
	with open(DATAFOLDER + BATTLEFILE) as file:
	 	data = file.read()
	 	parser = PokemonShowdownReplayParser(data)
	 	parser.run()

	'''
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
			print("================================================")
		counter += 1
	

if __name__ == "__main__":
	main()
