import re

DATAFOLDER = '../../data/replays/'
BATTLEFILE = 'gen7randombattle-567041326.log'

class PokemonShowdownReplayParser(object):
	def __init__(self, log="", players={}):
		self.log = log
		self.players = players
		self.players["p1"] = Player("p1")
		self.players["p2"] = Player("p2")

	def run(self):
		self.parse()

		output = ""
		output += self.players["p1"].getTeamFormatString()
		output += self.players["p2"].getTeamFormatString()

		return output

	def parse(self):
		lines = self.log.split('\n')
		for line in lines:
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
					or line.startswith("|turn|")
					or line.startswith("|-sidestart|")
					or line.startswith("|-start|")
					or line.startswith("|-damage|")
					or line.startswith("|-fail|")
					or line.startswith("|-activate|")
					or line.startswith("|-boost|")
					or line.startswith("|start")
					or line.startswith("|faint|")
					or line.startswith("|win|")
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

	def processPlayer(self, line):
		fields = line.split("|")

		if len(fields) >= 4:
			self.players[fields[2]].username = fields[3]


	def processPoke(self, line):
		fields = line.split("|")

		pokemon = Pokemon()
		pokemon.species = fields[3].replace("/,.*$/", "")
		self.players[fields[2]].pokemon.append(pokemon)


	def processSwitch(self, line):
		matches = re.search("\|switch\|(p[12])a:\s+([^|]+)\|([^,|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		print("###"+line)
		print(self.players[player])
		pokemon = self.players[player].getPokemonBySpecies(species)
		if pokemon == None:
			pokemon = Pokemon()
			pokemon.species = species
			self.players[player].pokemon.append(pokemon)
		pokemon.nickname = nickname
		self.players[player].currentPokemon = pokemon


	def processMove(self, line):
		matches = re.search("\|move\|(p[12])a:\s+([^|]+)\|([^|]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		move = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.moves[move] = 1


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
		# var species = matches[2]
		megastone = matches[3]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.item = megastone


	def processDetailsChange(self, line):
		matches = re.search("\|detailschange\|(p[12])a:\s+([^|]+)\|([^,]+)", line).groups()
		player = matches[0]
		nickname = matches[1]
		species = matches[2]

		pokemon = self.players[player].getPokemonByNickname(nickname)
		pokemon.species = species


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



class Player(object):
	def __init__(self, name="", username="", pokemon=[], currentPokemon=None):
		self.name = name
		self.username = username
		self.pokemon = pokemon
		self.currentPokemon = currentPokemon

	def getPokemonBySpecies(self, species):
		for i in range(len(self.pokemon)):
			if self.pokemon[i].species == species:
				return self.pokemon[i]
		return None


	def getPokemonByNickname(self, nickname):
		for i in range(len(self.pokemon)):
			if self.pokemon[i].nickname == nickname:
				return self.pokemon[i]
		return None


	def getTeamFormatString(self):
		output = "-------------------------\n"
		output += "Player: "+self.username+"\n"
		output += "-------------------------\n"
		for i in range(len(self.pokemon)):
			output += self.pokemon[i].getTeamFormatString() + "\n"
		return output


class Pokemon(object):
	def __init__(self, species="", nickname="", item="", ability="", moves={}):
		self.species = species
		self.nickname = nickname
		self.item = item
		self.ability = ability
		self.moves = moves

	def getTeamFormatString(self):
		s = ""
		s += self.species + " @ " + self.item +"\n"
		s += "Ability: "+ self.ability + "\n"
		for move in self.moves:
			s += "- " + move + "\n"
		return s

def main():
	with open(DATAFOLDER + BATTLEFILE) as file:
		data = file.read()

	parser = PokemonShowdownReplayParser(data)
	parser.run()

if __name__ == "__main__":
	main()
