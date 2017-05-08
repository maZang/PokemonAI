class Pokemon(object):
	def __init__(self, species="", nickname="", item="", ability="", status="", health=100):
		self.species = species
		self.nickname = nickname
		self.item = item
		self.ability = ability
		self.status = status
		self.moves = set()
		self.health = 100

	def __repr__(self):
		return "(Pokemon: (species={}, nickname={}, item={}, ability={}, status={}, moves={}, health={}))".format(self.species, self.nickname, self.item, self.ability, self.status, self.moves, self.health)

	def getTeamFormatString(self):
		s = ""
		s += self.species + " @ " + self.item +"\n"
		s += "Ability: " + self.ability + "\n"
		for move in self.moves:
			s += "- " + move + "\n"
		print(s + "\n")
		return s

	def resetMega(self):
		if "-Mega" in self.species or "-Primal" in self.species:
			self.species = self.species.split('-')[0]