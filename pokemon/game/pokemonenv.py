from reinforcement.environment import Environment
from learner.approxqlearner import PokemonShowdownAI
from learner.approxqlearner import AIConfig, AIConfig2, AIConfig3
from learner.pokemonfeat import PokemonAINetwork
from learner.pokemonfeat2 import PokemonAINetwork2
from learner.pokemonfeat3 import PokemonAINetwork3
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException

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
	learner=PokemonShowdownAI
	network=PokemonAINetwork3
	config=AIConfig3


class PokemonShowdownConfigSelfPlay(object):
	user='CS6700AITest'
	password='HORSERADISHBACON'
	learner=PokemonShowdownAI
	network=PokemonAINetwork3
	config=AIConfig3


class PokemonShowdown(Environment):
	def __init__(self, config, driver, username):
		self.learner = config.learner(self, lambda x: x, config.network, {'buffer_size' : 1000}, config.config(), config.user)
		self.driver = driver

		self.player = Player(username=username)
		self.opponent = Player()

		# Player that made the most recent move
		self.lastMovePlayer = ""
		# If the most recent move failed
		self.lastMoveFailed = False
		# If the player move failed due to par, slp, taunt, flinch, etc.
		self.playerCantMove = False

		self.opponentLastMove = 0

		# If the player knocks an opponent pokemon out
		self.playerKnockout = False

		self.winner = False
		self.finished = False

		self.turnNumber = -1

		self.pokemon = [np.zeros((1, POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.other_data = np.zeros((1, NON_EMBEDDING_DATA))
		self.last_move_data = np.zeros((1, 2))

	def setNewEpisode(self):
		self.player = Player(username=self.player.username)
		self.opponent = Player()

		self.lastMovePlayer = ""
		self.lastMoveFailed = False
		self.playerCantMove = False

		self.opponentLastMove = 0

		self.playerKnockout = False

		self.winner = False
		self.finished = False

		self.turnNumber = -1

		self.pokemon = [np.zeros((1, POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.other_data = np.zeros((1, NON_EMBEDDING_DATA))
		self.last_move_data = np.zeros((1, 2))

	def pad(self, actionList):
		return actionList + [0] * (MAX_ACTIONS - len(actionList))

	def encodeCurrentState(self, action=None):
		'''
		Encode the current state of the environment.
		We assume that refreshLogs will have been called at this point
		'''
		self.reset()

		# Stall until we can click something
		self.wait()

		self.refresh()

		self.pullMega()
		self.encodeAllPokemon()

		if action:
			self.last_move_data[0][0] = action

		if self.playerCantMove:
			self.last_move_data[0][0] = 0

		if self.opponentLastMove:
			self.last_move_data[0][1] = self.opponentLastMove


		return [np.copy(pokemon) for pokemon in self.pokemon] + [np.copy(self.other_data)] + [np.copy(self.last_move_data)] + [np.array(self.pad(self.actionList)).reshape(1,-1)]

	def pullMega(self):
		# Pull mega if exists
		# Note that this is a bottleneck since we implicitly wait and
		# there is no mega usually
		self.driver.implicitly_wait(0.5)
		if self.driver.find_elements(By.NAME, 'megaevo'):
			currPokemon = self.player.currentPokemon.species
			if currPokemon in ['Charizard', 'Mewtwo'] and self.player.currentPokemon.item:
				currPokemon += '-Mega-' + self.player.currentPokemon.item[-1].upper()
			else:
				currPokemon += '-Mega'
			self.actionList[-1] = POKEMON_LIST[currPokemon]
		self.driver.implicitly_wait(5)

	def encodeAllPokemon(self):
		self.pokemonEncoding = {}
		self.pokemonEncoding[0] = [encodeEnvPokemonObject(Pokemon())]*12

		self.encodePokemon(opponent=False)
		self.encodePokemon(opponent=True)

		for turnNumber, lst in self.pokemonEncoding.items():
			for i in range(0, 12):
				self.pokemon[i][turnNumber] = lst[i][:, :POKE_DESCRIPTOR_SIZE]
				self.other_data[turnNumber, i] = lst[i][:, POKE_DESCRIPTOR_SIZE] / 100.

	def encodePokemon(self, opponent=False):
		if opponent:
			player = self.opponent
		else:
			player = self.player

		currentPokemon = player.currentPokemon
		if not currentPokemon:
			print("Player had no current Pokemon.")
			return

		idx = 6 if opponent else 0

		# 0-5 = Winner's pokemon, 6-11 = Opponent's pokemon
		# Turn number : list of 12 pokemon that represents
		self.pokemonEncoding[0][idx] = encodeEnvPokemonObject(currentPokemon)

		i = 1
		print(player.pokemon)
		for pokemon in player.pokemon:
			if pokemon == currentPokemon:
				continue
			self.pokemonEncoding[0][i+idx] = encodeEnvPokemonObject(pokemon)
			i += 1

	def getActions(self, state=None):
		'''
		Returns list of pokemonIDs to switch to, moveIDs, or mega Pokemon ID if mega
		'''
		if state != None:
			return state[-1]
		self.actionList = []

		try:
			moveCount = 0
			for move in self.driver.find_elements(By.NAME, 'chooseMove'):
				if move:
					self.actionList.append(MOVE_LIST[move.text.split("\n")[0]])
					moveCount += 1

			for pokemon in self.driver.find_elements(By.NAME, 'chooseSwitch'):
				if pokemon:
					self.actionList.append(POKEMON_LIST[pokemon.text])

			# U-Turn parse
			if moveCount == 0 and len(self.driver.find_elements(By.NAME, 'chooseMove')) > 0:
				self.actionList = []
				return
		except StaleElementReferenceException as e:
			self.actionList = []

		print("Actions found: {}".format(self.actionList))

		if len(self.actionList) > 0 and len(self.actionList) < MAX_ACTIONS:
			self.actionList.extend([0] * (MAX_ACTIONS - len(self.actionList)))

		return self.actionList

	def reset(self):
		'''
		Resets the environment to the start state
		'''
		# One row encoding
		self.pokemon = [np.zeros((1, POKE_DESCRIPTOR_SIZE)) for _ in range(12)]
		self.other_data = np.zeros((1, NON_EMBEDDING_DATA))

	def run(self):
		currentState = self.encodeCurrentState()
		while True:
			print("Current state: {}".format(currentState))

			action = self.learner.getAction(currentState)
			self.update(action)
			# Reset last move matrix
			self.last_move_data = np.zeros((1, 2))
			# After a move is clicked, the state is updated, now retrieve next state
			nextState = self.encodeCurrentState(action)
			# Check if we won
			reward = 0
			if self.lastMoveFailed:
				reward += -0.05
			if self.playerKnockout:
				reward += 0.1

			# Reset reward modifiers
			self.lastMoveFailed = False
			self.playerKnockout = False

			self.playerCantMove = False

			if self.finished:
				print(nextState)
				reward += (1 if self.winner else -1)
			print(reward)
			self.learner.update(currentState, action, nextState, reward, np.abs(reward))

			currentState = nextState

			if self.finished:
				self.learner.updateEpisodeNumber()
				return

	def wait(self):
		'''
		Stalls until an action is available
		'''
		while True:
			print("Retrieving actions...")
			print(self.finished)
			self.getActions()
			if len(self.actionList) > 0 or self.finished:
				return
			else:
				time.sleep(1)
				self.refresh()

	def update(self, action):
		'''
		Clicks the move/switch/mega
		'''
		# Switch/mega
		print("ID {} received:".format(action))
		if action in REV_POKEMON_LIST:
			pokemon = REV_POKEMON_LIST[action]
			print(pokemon)
			if '-mega' in pokemon.lower():
				# Unparse the -Mega
				pokemon = pokemon.split('-')[0]

			found = False
			# Scan list of switchable pokemon
			for pkmn in self.driver.find_elements(By.NAME, 'chooseSwitch'):
				if pkmn and pkmn.text == pokemon:
					pkmn.click()
					found = True
					break
			# List of switchable pokemon was not the pokemon, thus it must be a mega-evolve
			if not found:
				print("{}: Megaevolving {}.".format(self.player.username, pokemon))
				driver_find_element(self.driver, By.NAME, 'megaevo').click()
			else:
				print("{}: Switch action received. Switching to {}.".format(self.player.username, pokemon))

		elif action in REV_MOVE_LIST:
			# Action is a move
			move = REV_MOVE_LIST[action]
			idx = None
			if move in ['Hidden Power', 'Return']:
				for m in self.driver.find_elements(By.NAME, 'chooseMove'):
					if move in m.text:
						print("Move was in m.text")
						# TODO: figure out why this isn't being clicked
						m.click()
						break
			else:
				driver_find_element(self.driver, By.CSS_SELECTOR, 'button[data-move="{}"]'.format(move)).click()
			print("{}: Move action received. Using move {}.".format(self.player.username, move))
		else:
			raise Exception("ID {} was not a pokemon/move ID".format(move))

	def refreshLogs(self):
		logs = self.driver.get_log('browser')

		lines = []
		for entry in logs:
			message = '|' + entry['message'].partition('|')[2]
			split = message.split('\\n')
			for line in split:
				lines.append(line)

		for line in lines:
			print(line)
			self.parseLine(line)

		for pokemon in self.opponent.pokemon:
			print(pokemon)

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
		elif line.startswith("|cant|"):
			self.processCant(line)
		elif line.startswith("|-fail|"):
			self.processFail(line)
		elif line.startswith("|-immune|"):
			self.processImmune(line)
		elif line.startswith("|-boost|"):
			self.processBoost(line)
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

		if player == self.opponent.name:
			if "Arceus" in species:
				species = "Arceus"
			elif "Gourgeist" in species:
				species = "Gourgeist"
			elif "Genesect" in species:
				species = "Genesect"

			pokemon = Pokemon()
			pokemon.species = species
			if "Gourgeist" in species:
				print("Setting pokemon nickname to Gourgeist")
				pokemon.nickname = "Gourgeist"
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

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species)
			elif "Gourgeist" in species:
				print("Gourgeist if statement is entered.")
				print("Species: " + species)
				self.prefixHandler("Gourgeist", species)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species)

			pokemon = self.opponent.getPokemonBySpecies(species)

			if pokemon == None and "Gourgeist-Small" in species:
				print("No pokemon was found with species: " + species)
				pokemon = self.opponent.getPokemonByNickname("Gourgeist")
				if pokemon is not None:
					pokemon.species = species

			if pokemon == None:
				pokemon = Pokemon()
				pokemon.nickname = nickname
				pokemon.species = species
				self.opponent.pokemon.append(pokemon)
				# assert(len(self.opponent.pokemon) <= 6)
			elif pokemon.nickname == "":
				pokemon.nickname = nickname
			self.opponent.currentPokemon = pokemon
			self.opponentLastMove = POKEMON_LIST[pokemon.species]

	def processDrag(self, line):
		matches = re.search("\|drag\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2].split(',')[0]

		if player == self.opponent.name:
			# Special prefix edge case.
			if "Arceus" in species:
				self.prefixHandler("Arceus", species)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species)
			elif "Gourgeist-Small" == species:
				print("Species is Gourgeist-Small.")
				self.prefixHandler("Gourgeist", species)

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
				self.prefixHandler("Arceus", species)
			elif "Gourgeist" in species:
				self.prefixHandler("Gourgeist", species)
			elif "Genesect" in species:
				self.prefixHandler("Genesect", species)
			elif "Gourgeist-Small" == species:
				print("Species is Gourgeist-Small.")
				self.prefixHandler("Gourgeist", species)

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

		if "[from]Magic Bounce" not in line:
			self.lastMovePlayer = player

		if player == self.opponent.name:
			self.opponentLastMove = MOVE_ENV_LIST[move]

			pokemon = self.opponent.getPokemonByNickname(nickname)

			# This is so that moves from Magic Bounce and "Struggle" aren't added to moveset.
			if "[from]" not in line and "Struggle" not in line:
				pokemon.moves.add(move)

			assert(len(pokemon.moves) <= 4)

	def processCant(self, line):
		matches = re.search("\|cant\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		reason = matches[2]

		if player == self.player.name:
			print("Player failed to use move (flinch, slp, par, taunt, etc)")
			self.playerCantMove = True

	def processFail(self, line):
		if self.lastMovePlayer == self.player.name:
			print("Last move failed.")
			self.lastMoveFailed = True

	def processImmune(self, line):
		if self.lastMovePlayer == self.player.name:
			print("Last move immune.")
			self.lastMoveFailed = True

	def processBoost(self, line):
		matches = re.search("\|-boost\|(p[12])a:\s+([^|]+)\|([^\n|]+)\|([^\n|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		stat = matches[2]
		boost = matches[3]

		if self.lastMovePlayer == self.player.name and boost == "0":
			print("Boost failed.")
			self.lastMoveFailed = True

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
		health = int(matches[2].split('/')[0])

		if player == self.opponent.name:
			pokemon = self.opponent.getPokemonByNickname(nickname)
			pokemon.health = health
			if health == 0:
				print("Player knocked opponent pokemon out.")
				self.playerKnockout = True

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
			pokemon.item = ""

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

			if condition == "0 fnt":
				currHP = 0
				status = ""
			else:
				matches = re.search("(\d*)\/(\d*) *(\D*)", condition).groups()
				maxHP = int(matches[1])
				# Normalize HP so that it's out of 100.
				currHP = int(int(matches[0]) * 100 / maxHP)
				status = matches[2]

			# Active is true or false.
			active = poke_data["active"]

			# Moves is a list of strings.
			moves = poke_data["moves"]
			for i in range(len(moves)):
				moves[i] = re.sub("\d+", "", moves[i])

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
		winnerUsername = fields[2][:-1]
		if self.player.username == winnerUsername:
			self.winner = True
		else:
			self.winner = False

		self.finished = True

DRIVERFOLDER = 'driver/chromedriver'
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

def driver_find_element(driver, by_type, id, secs=0.5):
	while True:
		try:
			element = WebDriverWait(driver, secs).until(
				EC.presence_of_element_located((by_type, id))
			)
		except TimeoutException as e:
			continue
		break
	return element

def driver_find_elements(driver, by_type, id, secs=0.5):
	while True:
		try:
			elements = WebDriverWait(driver, secs).until(
				EC.presence_of_all_elements_located((by_type, id))
			)
		except TimeoutException as e:
			continue
		break
	return elements


def challenge(driver, user=None):
	if user:
		while True:
			try:
				time.sleep(1.5)
				driver_find_element(driver, By.NAME, "finduser").click()
				time.sleep(0.5)
				driver_find_element(driver, By.NAME, "data").clear()
				driver_find_element(driver, By.NAME, "data").send_keys(user)
				driver_find_element(driver, By.CSS_SELECTOR, 'button[type="submit"]').click()
				time.sleep(0.5)
				driver_find_element(driver, By.NAME, "challenge").click()
				driver_find_element(driver, By.CSS_SELECTOR, 'button[class="select formatselect"]').click()
				driver_find_element(driver, By.CSS_SELECTOR, 'button[value="battlefactory"]').click()
				driver_find_element(driver, By.NAME, "makeChallenge").click()
				time.sleep(0.5)

				for pokemon in driver_find_elements(driver, By.NAME, "chooseTeamPreview"):
					if pokemon.text == 'Zoroark':
						while True:
							try:
								for elem in driver_find_elements(driver, By.NAME, "chooseTeamPreview"):
									elem.click()
							except StaleElementReferenceException as e:
								continue
							break
						break

				driver_find_element(driver, By.CSS_SELECTOR, 'button[value="0"]').click()
			except (NoSuchElementException,AttributeError) as e:
				time.sleep(0.5)
				driver_find_element(driver, By.NAME, "close", 10).click()
				continue
			break
	else:
		while True:
			try:
				driver.find_element(By.NAME, "acceptChallenge").click()
			except NoSuchElementException as e:
				time.sleep(0.5)
				continue
			except AttributeError as e:
				time.sleep(0.5)
				continue
			break
		time.sleep(0.5)

		for pokemon in driver_find_elements(driver, By.NAME, "chooseTeamPreview"):
			if pokemon.text == 'Zoroark':
				for elem in driver_find_elements(driver, By.NAME, "chooseTeamPreview"):
					elem.click()
				break

		driver.find_element(By.CSS_SELECTOR, 'button[value="0"]').click()
		time.sleep(0.5)

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself(isOpponent=False):
	if not isOpponent:
		showdown_config = PokemonShowdownConfig()
	else:
		showdown_config = PokemonShowdownConfigSelfPlay()

	options = Options()
	options.add_argument("--disable-notifications")
	options.add_argument("--mute-audio")
	d = DesiredCapabilities.CHROME
	d['loggingPrefs'] = { 'browser':'INFO' }
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=options, desired_capabilities=d)
	driver.implicitly_wait(5)
	login(driver, showdown_config)

	if not isOpponent:
		# Challenge that user
		challenge(driver, user=PokemonShowdownConfigSelfPlay().user)
	else:
		challenge(driver)

	env = PokemonShowdown(showdown_config, driver, showdown_config.user)
	env.refresh()

	while True:
		env.run()
		print("Game finished.")
		print("Resetting")
		env.setNewEpisode()
		if not isOpponent:
			# Challenge that user
			driver.get(BASEURL)
			time.sleep(0.5)
			challenge(driver, user=PokemonShowdownConfigSelfPlay().user)
		else:
			while True:
				try:
					driver.find_element(By.NAME, "closeRoom").click()
				except:
					continue
				break
			time.sleep(0.5)
			challenge(driver)
