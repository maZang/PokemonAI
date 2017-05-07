from reinforcement.environment import Environment
from learner.approxqlearner import ApproxQLearner
from selenium import webdriver
from selenium.webdriver.common.by import By

from datautils.const import *
from datautils.encoding import *
from datautils.player import *
from datautils.pokemon import *
from datautils.turn import *

import json
import time


class PokemonShowdownConfig(object):
	'''
	Config for Pokemon showdown
	'''
	user='CS6700AI'
	password='HORSERADISHBACON'
	learner=ApproxQLearner


class PokemonShowdownConfigSelfPlay(object):
	user='CS6700AITest'
	password='HORSERADISHBACON'
	learner=ApproxQLearner


class PokemonShowdown(Environment):
	def __init__(self, config, driver, username):
		self.learner = config.learner
		self.driver = driver

		self.player = Player(username=username)
		self.opponent = Player()

	def getCurrentState(self):
		'''
		Gets the current state of the environment.
		'''
		pass

	def getActions(self, state=None):
		'''
		Returns the actions possible for the current state. If state=None, return all actions.
		'''
		pass

	def reset(self):
		'''
		Resets the environment to the start state
		'''
		pass

	def update(self, action):
		'''
		Updates the state based upon the current state and action. Returns the new state
		and a reward
		'''
		pass

	def isEndState(self):
		'''
		Checks if it is an end state, e.g. the episode is over
		'''
		pass

	def processPlayer(self, line):
		fields = line.split("|")
		player = fields[2]
		username = fields[3]

		if username == self.player.username:
			# Sets name to "p1" or "p2".
			self.player.name = player
		else:
			self.opponent.name = player
			self.opponent.username = username

	def processPoke(self, line):
		fields = line.split("|")
		player = fields[2]
		species = fields[3].replace("/,.*$/", "").split(',')[0]

		if player == self.opponent.name:
			if "Arceus" in species:
				species = "Arceus"
			elif "Gourgeist" in species:
				species = "Gourgeist"
			elif "Genesect" in species:
				species = "Genesect"

			pokemon = Pokemon()
			pokemon.species = species
			self.opponent.pokemon.append(pokemon)

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

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species, player)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species, player)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species, player)

			pokemon = self.opponent.getPokemonBySpecies(species)

			if pokemon == None:
				pokemon = Pokemon()
				pokemon.nickname = nickname
				pokemon.species = species
				self.players[player].pokemon.append(pokemon)
				assert(len(self.players[player].pokemon) <= 6)
			elif pokemon.nickname == "":
				pokemon.nickname = nickname
			self.opponent.currentPokemon = pokemon

	def processDrag(self, line):
		matches = re.search("\|drag\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species, player)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species, player)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species, player)

			pokemon = self.opponent.getPokemonBySpecies(species)

			if pokemon == None:
				pokemon = Pokemon()
				pokemon.nickname = nickname
				pokemon.species = species
				self.players[player].pokemon.append(pokemon)
				assert(len(self.players[player].pokemon) <= 6)
			elif pokemon.nickname == "":
				pokemon.nickname = nickname
			self.opponent.currentPokemon = pokemon

	def processReplace(self, line):
		matches = re.search("\|replace\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species, player)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species, player)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species, player)

			pokemon = self.opponent.getPokemonBySpecies(species)

			if pokemon == None:
				pokemon = Pokemon()
				pokemon.nickname = nickname
				pokemon.species = species
				self.players[player].pokemon.append(pokemon)
				assert(len(self.players[player].pokemon) <= 6)
			elif pokemon.nickname == "":
				pokemon.nickname = nickname
			self.opponent.currentPokemon = pokemon

	def processMove(self, line):
		matches = re.search("\|move\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		move = matches[2].lower().replace("-", "").replace(" ", "").replace("'", "")

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)

			# This is so that moves from Magic Bounce and "Struggle" aren't added to moveset.
			if "[from]" not in line and "Struggle" not in line:
				pokemon.moves.add(move)

			assert(len(pokemon.moves) <= 4)

	def processMega(self, line):
		matches = re.search("\|-mega\|(p[12])a:\s+([^|]+)\|([^|]+)\|(.+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		# species = matches[2]
		megastone = matches[3].lower().replace("-", "").replace(" ", "").replace("'", "")

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.item = megastone

	def processDetailsChange(self, line):
		matches = re.search("\|detailschange\|(p[12])a:\s+([^|]+)\|([^\n]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.species = species

	def processStatus(self, line):
		matches = re.search("\|-status\|(p[12])a:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		status = matches[2]

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.status = status

	def processCureStatus(self, line):
		matches = re.search("\|-curestatus\|(p[12])a{0,1}:\s+([^|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.status = ""

	def processDamage(self, line):
		matches = re.search("\|-damage\|(p[12])a:\s+([^|]+)\|([\d]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		health = matches[2].split('/')[0]

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.health = health

	def processItemFromMove(self, line):
		matches = re.search("\|-item\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2].lower().replace("-", "").replace(" ", "").replace("'", "")

		if player == self.opponent.name:
			otherPokemon = self.opponent.currentPokemon

			if otherPokemon.item == "":
				otherPokemon.item = item

	def processEndItem(self, line):
		matches = re.search("\|-enditem\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2].lower().replace("-", "").replace(" ", "").replace("'", "")

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			if pokemon.item == "":
				pokemon.item = item

	def processHealFromItem(self, line):
		matches = re.search("\|-heal\|(p[12])a:\s+([^|]+)\|[^|]+\|\[from\] item: (.+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		item = matches[2].lower().replace("-", "").replace(" ", "").replace("'", "")

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.item = item

	def processHeal(self, line):
		matches = re.search("\|-heal\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		health = matches[2].split('/')[0]

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.health = health

	def processRequest(self, line):
		'''
		Processes a request line. Every request line gives a complete update of our team in JSON form.
		'''
		matches = re.search("\|request\|(.*)", line).groups()
		data_string = matches[0]

		# Convert data to JSON.
		data = json.loads(data_string)
		self.player.pokemon = []

		self.parseStateFromJSON(data)


	def parseStateFromJSON(self, data):
		'''
		Parses the JSON printed from console.log.
		'''
		for poke_data in data["side"]["pokemon"]:
			# Nickname string is in the form "p1: Blastoise", where Blastoise is the nickname.
			nickname = re.search("p[12]: (.*)", poke_data["ident"]).groups()[0]

			species = poke_data["details"].split(',')[0]

			# condition is in the format "CurrHP/TotalHP STATUS", ex. "250/301 tox", or just "250/301"
			condition = poke_data["condition"]
			matches = re.search("(\d*)\/(\d*) *(\D*)", condition).groups()
			maxHP = int(matches[1])
			# Normalize HP so that it's out of 100.
			currHP = int(matches[0]) * 100 / maxHP

			status = matches[2]

			# Active is true or false.
			active = poke_data["active"]

			# Moves is a list of strings.
			moves = poke_data["moves"]

			if "item" in poke_data:
				item = poke_data["item"]
			else:
				item = ""

			pokemon = Pokemon(species=species, nickname=nickname, item=item, status=status, health=currHP)
			pokemon.moves = set(moves)

			if active:
				self.player.currentPokemon = pokemon

			self.player.pokemon.append(pokemon)


DRIVERFOLDER = 'driver/chromedriver.exe'
BASEURL = 'http://play.pokemonshowdown.com/'

def login(driver, showdown_config):
	driver.get(BASEURL)
	time.sleep(1)
	driver.find_element(By.NAME, "login").click()
	time.sleep(1)
	driver.find_element(By.NAME, "username").clear()
	time.sleep(1)
	driver.find_element(By.NAME, "username").send_keys(showdown_config.user)
	time.sleep(1)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(1)
	driver.find_element(By.NAME, "password").clear()
	time.sleep(1)
	driver.find_element(By.NAME, "password").send_keys(showdown_config.password)
	time.sleep(1)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(1)

def challenge(driver1, driver2, showdown_config1, showdown_config2):
	driver1.find_element(By.NAME, "finduser").click()
	time.sleep(1)
	driver1.find_element(By.NAME, "data").clear()
	time.sleep(1)
	driver1.find_element(By.NAME, "data").send_keys(showdown_config2.user)

def analyzeLog(driver):
	data = driver.get_log('browser')
	print(data)

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself():
	showdown_config1 = PokemonShowdownConfig()
	showdown_config2 = PokemonShowdownConfigSelfPlay()
	driver1 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	driver2 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver1, showdown_config1)
	login(driver2, showdown_config2)
	challenge(driver1, driver2, showdown_config1, showdown_config2)
