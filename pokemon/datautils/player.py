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
			output += pokemon.getTeamFormatString() + "\n"
		return output

	def resetPokemon(self):
		'''
		Resets all pokemon except species and nickname.
		'''
		self.currentPokemon = None
		for pokemon in self.pokemon:
			pokemon.item = ""
			pokemon.ability = ""
			pokemon.status = ""
			pokemon.moves = set()
			pokemon.resetMega()

	def resetStatuses(self):
		'''
		Resets pokemon statuses.
		'''
		for pokemon in self.pokemon:
			pokemon.status = ""

	def resetMega(self):
		'''
		Resets mega evolution.
		'''
		for pokemon in self.pokemon:
			pokemon.resetMega()