from reinforcement.environment import Environment
from learner.approxqlearner import ApproxQLearner
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from datautils.const import *
from datautils.encoding import *
from datautils.player import *
from datautils.pokemon import *
from datautils.turn import *

import json
import re
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


class Entry(object):
	"""An entry in the game log"""
	def __init__(self, ID, text):
		self.ID = ID
		self.text = str(text)
		self.handled = False

	def __str__(self):
		if not self.handled:
			return("Unhandled entry with ID: " + str(self.ID) + " and text " + self.text)
		else:
			return("Handled entry with ID: " + str(self.ID) + " and text " + self.text)

	__repr__ = __str__


class EntryManager(object):
	"""Handles entries to make sure that we process each"""
	def __init__(self):
		"""Start with an empty list of entries"""
		self.entry_list = []
		self.entry_IDs = []

	def register_entries(self, entries):
		"""Register new entries into our list if we don't have them already"""
		new_entries = [[i,x] for i,x in enumerate(entries) if i not in self.entry_IDs]
		for entry in new_entries:
			self.entry_list.append(Entry(entry[0],entry[1]))

		self.entry_IDs = [x.ID for x in self.entry_list]

	def get_unhandled_entries(self):
		"""Return any entries not yet handled."""
		return([x for x in self.entry_list if not x.handled])


class PokemonShowdown(Environment):
	def __init__(self, config, driver, username):
		self.learner = config.learner
		self.driver = driver

		self.player = Player(username=username)
		self.opponent = Player()

		self.winner = False
		self.finished = False

		self.entry_manager = EntryManager()
		self.turnNumber = -1

		self.last_move_data = np.zeros((1, 2))

	def getCurrentState(self, action=None):
		'''
		Gets the current state of the environment.
		We assume that refreshLogs will have been called at this point
		'''
		self.reset()
		self.encodeAllPokemon()

		self.labels[action] = 1
		if action and self.opponentAction:
			self.last_move_data[0][0] = action
			# After performing the move, retrieve the opponent's move
			self.last_move_data[0][1] = self.opponentAction


	def encodeAllPokemon(self):
		self.pokemonEncoding = {}
		self.pokemonEncoding[0] = [encodePokemonObject(Pokemon())]*12

		self.encodePokemon("p1")
		self.encodePokemon("p2")

		for turnNumber, lst in self.pokemonEncoding.items():
			for i in range(0, 12):
				self.pokemon[i][turnNumber] = lst[i][:, :POKE_DESCRIPTOR_SIZE]
				self.other_data[turnNumber, i] = lst[i][:, POKE_DESCRIPTOR_SIZE] / 100.

	def encodePokemon(self, player):
		playerPokemon = self.players[player]
		currentPokemon = self.players[player].currentPokemon
		if not currentPokemon:
			return

		idx = 0
		if player != self.winner:
			idx = 6

		# 0-5 = Winner's pokemon, 6-11 = Opponent's pokemon
		# Turn number : list of 12 pokemon that represents
		self.pokemonEncoding[0][idx] = encodePokemonObject(currentPokemon)

		i = 1
		for pokemon in playerPokemon.pokemon:
			if pokemon == currentPokemon:
				continue
			self.pokemonEncoding[0][i+idx] = encodePokemonObject(pokemon)
			i += 1

	def getActions(self, state=None):
		'''
		Returns the actions possible for the current state. If state=None, return all actions.
		'''
		# List of pokemonIDs to switch to, moveIDs to move, or mega Pokemon ID if mega
		actionList = []

		for move in self.driver.find_elements(By.NAME, 'chooseMove'):
			if move:
				actionList.append[MOVE_LIST[move.text.split("\n")[0]]]
		for pokemon in self.driver.find_elements(By.NAME, 'chooseSwitch'):
			if pokemon:
				actionList.append[POKEMON_LIST[pokemon.text]]

		time.sleep(1)

		# Pull mega if exists
		if self.driver.find_elements(By.NAME, 'megaevo'):
			currPokemon = self.player.currentPokemon.species
			if currPokemon in ['Charizard', 'Mewtwo'] and currPokemon.item:
				currPokemon += '-Mega-' + currPokemon.item[-1]
			else:
				currPokemon += '-Mega'
			actionList.append[currPokemon]

		return actionList

	def reset(self):
		'''
		Resets the environment to the start state
		'''
		# One row encoding
		self.pokemon = [np.zeros((1, POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.labels = np.zeros((1, NUMBER_CLASSES))

	def run(self):
		while True:
			currentState = self.getCurrentState()
			actions = self.getActions()
			if not actions:
				time.sleep(1)
				continue

			action = self.learner.getAction(currentState, actions)
			self.update(action)
			reward = self.isWonGame()

			# Reset last move matrix
			self.last_move_data = np.zeros((1, 2))
			# After a move is clicked, the state is updated, now retrieve next state
			nextState = self.getCurrentState(action)
			self.learner.update(currentState, action, nextState, reward)

			if reward:
				return

	def update(self, action):
		'''
		Clicks the move/switch/mega
		'''
		# Switch/mega
		print("ID {} received:".format(action))
		if action in REV_POKEMON_LIST:
			pokemon = REV_POKEMON_LIST[action]
			if '-mega' in pokemon.lower():
				# Unparse the -Mega
				pokemon = pokemon.split('-')[0]
			print("{}: Switch action received. Switching to {}".format(self.player.username, pokemon))

			idx = 1
			found = False
			# Scan list of switchable pokemon
			for pkmn in self.driver.find_elements(By.NAME, 'chooseSwitch'):
				if pkmn and pkmn.text == pokemon:
					css = 'button[name="chooseSwitch"][value="{}"]'.format(idx)
					self.driver.find_element(By.CSS_SELECTOR, css).click()
					found = True
					break
				idx += 1
				print(pkmn.text)

			# List of switchable pokemon was not the pokemon, thus it must be a mega-evolve
			if not found:
				print("{}: Megaevolving {}.".format(self.player.username, pokemon))
				self.driver.find_element(By.NAME, 'megaevo').click()
		elif action in REV_MOVE_LIST:
			# Action is a move
			move = REV_MOVE_LIST[action]
			print("{}: Move action received. Using move {}".format(self.player.username, move))

			self.driver.find_element(By.CSS_SELECTOR, 'button[data-move="{}"]'.format(move)).click()
		else:
			raise Exception("ID {} was not a pokemon/move ID".format(move))

	def isWonGame(self):
		'''
		Check if the current player has won
		'''
		pass

	def refreshLogs(self):
		logs = self.driver.get_log('browser')

		lines = []
		for entry in logs:
			message = '|' + entry['message'].partition('|')[2]
			split = message.split('\\n')
			for line in split:
				lines.append(line)
				# pokemon_env.parseLine(line)

		self.entry_manager.register_entries(lines)

		new_entries = self.entry_manager.get_unhandled_entries()

		for entry_obj in new_entries:
			entry = entry_obj.text

			print(entry)

			self.parseLine(entry)

	def refresh(self):
		self.refreshLogs()

	def parseLine(self, line):
		if line.startswith("|player|"):
			self.processPlayer(line)
		elif line.startswith("|poke|"):
			self.processPoke(line)
		elif line.startswith("|switch|"):
			self.processSwitch(line)
		elif line.startswith("|drag|"):
			self.processDrag(line)
		elif line.startswith("|replace|"):
			self.processReplace(line)
		elif line.startswith("|move|"):
			self.processMove(line)
		elif line.startswith("|-mega|"):
			self.processMega(line)
		elif line.startswith("|detailschange|"):
			self.processDetailsChange(line)
		elif line.startswith("|-status|"):
			self.processStatus(line)
		elif line.startswith("|-curestatus|"):
			self.processCureStatus(line)
		elif line.startswith("|-damage|"):
			self.processDamage(line)
		elif line.startswith("|-enditem|"):
			self.processEndItem(line)
		elif line.startswith("|request|"):
			self.processRequest(line)
		elif "|[from] move:" in line:
			if line.startswith("|-item|"):
				self.processItemFromMove(line)
		elif "|[from] item:" in line:
			if line.startswith("|-heal|"):
				self.processHealFromItem(line)
				self.processHeal(line)
		elif line.startswith("|win|"):
			self.processWinner(line)
		else:
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

		# print(line)

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

	def prefixHandler(self, pokePrefix, species):
		'''
		Handles prefix edge cases. When pokemon are listed at the top of a battle log,
		their name is "Arceus-*". When they are switched in, they are listed as "Arceus-Ghost".
		This function sets the pokemon species to the specific species.

		Inputs:
		pokePrefix - Pokemon prefix.
		species - Pokemon species.
		'''
		pokemon = self.opponent.getPokemonBySpecies(pokePrefix)

		if pokemon != None:
			pokemon.species = species

	def processSwitch(self, line):
		matches = re.search("\|switch\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		# print(line)

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species)

			pokemon = self.opponent.getPokemonBySpecies(species)

			if pokemon == None:
				pokemon = Pokemon()
				pokemon.nickname = nickname
				pokemon.species = species
				self.opponent.pokemon.append(pokemon)
				assert(len(self.opponent.pokemon) <= 6)
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
				self.opponent.pokemon.append(pokemon)
				assert(len(self.opponent.pokemon) <= 6)
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
				self.opponent.pokemon.append(pokemon)
				assert(len(self.opponent.pokemon) <= 6)
			elif pokemon.nickname == "":
				pokemon.nickname = nickname
			self.opponent.currentPokemon = pokemon

	def processMove(self, line):
		matches = re.search("\|move\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		move = matches[2].lower().replace("-", "").replace(" ", "").replace("'", "")

		# print(line)

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
		data_string = matches[0].replace("\\", "")[:-1]

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

		assert(len(self.player.pokemon) <= 6)

		for pokemon in self.player.pokemon:
			print(pokemon)

	def processWinner(self, line):
		fields = line.split("|")

		assert(len(fields) >= 2)

		# Assigns username of winner
		winnerUsername = fields[2]

		if self.player.username == winnerUsername:
			self.winner = True
		else:
			self.winner = False

		self.finished = True

DRIVERFOLDER = 'driver/chromedriver.exe'
BASEURL = 'http://play.pokemonshowdown.com/'

def login(driver, showdown_config):
	driver.get(BASEURL)
	time.sleep(0.5)
	driver.find_element(By.NAME, "login").click()
	time.sleep(0.5)
	driver.find_element(By.NAME, "username").clear()
	driver.find_element(By.NAME, "username").send_keys(showdown_config.user)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)
	driver.find_element(By.NAME, "password").clear()
	driver.find_element(By.NAME, "password").send_keys(showdown_config.password)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)

def challenge(driver1, driver2, showdown_config1, showdown_config2):
	time.sleep(0.5)
	driver1.find_element(By.NAME, "finduser").click()
	time.sleep(0.5)
	driver1.find_element(By.NAME, "data").clear()
	driver1.find_element(By.NAME, "data").send_keys(showdown_config2.user)
	driver1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)
	driver1.find_element(By.NAME, "challenge").click()
	driver1.find_element(By.CSS_SELECTOR, 'button[class="select formatselect"]').click()
	driver1.find_element(By.CSS_SELECTOR, 'button[value="battlefactory"]').click()
	driver1.find_element(By.NAME, "makeChallenge").click()
	time.sleep(0.5)
	driver2.find_element(By.NAME, "acceptChallenge").click()
	time.sleep(0.5)
	driver1.find_element(By.CSS_SELECTOR, 'button[value="0"]').click()
	driver2.find_element(By.CSS_SELECTOR, 'button[value="0"]').click()
	time.sleep(0.5)

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself():
	showdown_config1 = PokemonShowdownConfig()
	showdown_config2 = PokemonShowdownConfigSelfPlay()
	options = Options()
	options.add_argument("--disable-notifications")
	options.add_argument("--mute-audio")
	d = DesiredCapabilities.CHROME
	d['loggingPrefs'] = { 'browser':'INFO' }
	driver1 = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=options, desired_capabilities=d)
	driver2 = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=options, desired_capabilities=d)
	driver1.implicitly_wait(30)
	driver2.implicitly_wait(30)
	login(driver1, showdown_config1)
	login(driver2, showdown_config2)
	challenge(driver1, driver2, showdown_config1, showdown_config2)

	env1 = PokemonShowdown(showdown_config1, driver1, showdown_config1.user)
	env2 = PokemonShowdown(showdown_config2, driver2, showdown_config2.user)
	for move in driver1.find_elements(By.NAME, 'chooseMove'):
		if move:
			env1.update(MOVE_LIST[move.text.split("\n")[0]])
			break
	time.sleep(1)
	for move in driver2.find_elements(By.NAME, 'chooseMove'):
		if move:
			print(move)
			env2.update(MOVE_LIST[move.text.split("\n")[0]])

	time.sleep(10)
