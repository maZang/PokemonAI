import numpy as np

from const import *
PARSED_FOLDER = 'data/parsed_replays/'

def encode(network_config, replay_file):
	encoding = PokemonShowdownEncoding.load(replay_file)
	return [encoding.pokemon + [encoding.other_data, encoding.last_move_data, encoding.labels]]


def getActionIDFromString(actionString, pokemon=None):
	# actionID is either a Pokemon actionID if that pokemon switched in
	# Move actionID if they used that move, or -1 if mega evolve
	if actionString in ['switch', 'mega']:
		actionID = POKEMON_LIST[pokemon]
	else:
		if actionString == 'Struggle':
			actionID = MOVE_LIST['<UNK>']
		else:
			actionID = MOVE_LIST[actionString]

	return actionID

def encodePokemonObject(pokemon):
	'''
	Encodes a pokemon object. Fills in any unknown moves/items with an unknown token.

	Input: Pokemon object
	Output: Pokemon encoding object with shape (1, POKE_DESCRIPTOR_SIZE)
	'''
	pokemon_encoding = np.zeros((1, POKE_DESCRIPTOR_SIZE))

	if pokemon.species == "Gourgeist":
		pokemon.species = "Gourgeist-Super"

	pokemon_id = POKEMON_LIST[pokemon.species or '<UNK>']

	move_ids = []

	# Encodes pokemon item
	item_id = ITEM_LIST[pokemon.item if pokemon.item in ITEM_LIST else '<UNK>']

	for move in pokemon.moves:
		move_ids.append(MOVE_LIST[move if move in MOVE_LIST else '<UNK>'])

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
		with open(PARSED_FOLDER + self.data_type + '/' + self.name + '.p', 'wb') as f:
			pickle.dump(self, f)

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
			for x in range(turnNumber, nextTurnNumber):
				self.last_move_data[x][1] = actionID

			if index + 1 == len(opponentTurnList) - 1:
				nextTurnNumber = self.num_turns
			else:
				index += 1
				nextTurnNumber = turnNumbers[index+1]

	def encodePokemon(self, pokemonEncoding):
		for turnNumber, lst in pokemonEncoding.iteritems():
			for i in range(0, 12):
				self.pokemon[i][turnNumber] = lst[i]