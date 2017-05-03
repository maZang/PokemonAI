class Turn(object):
	def __init__(self, turnNumber=None, player=None, action=None, pokemon=None, state=None):
		self.turnNumber = turnNumber
		self.player = player
		self.action = action
		self.pokemon = pokemon
		self.state = state

	def __repr__(self):
		return "(Turn {}: (player={}, action={}, pokemon={}, state={})".format(self.turnNumber, self.player, self.action, self.pokemon, self.state)