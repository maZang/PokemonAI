import pickle

POKEMON_FILE = 'data/info/pokemon.p'
ITEM_FILE = 'data/info/item.p'
MOVE_FILE = 'data/info/move.p'
POKE_DESCRIPTOR_SIZE = 7
POKE_META_SIZE = 1 # current health percentage
FIELD_META_SIZE = 0 # number of field status (e.g. weather) -- 0 for now
NON_EMBEDDING_DATA = 12 * POKE_META_SIZE + FIELD_META_SIZE
NUMBER_POKEMON = len(pickle.load(open(POKEMON_FILE, 'rb')))
NUMBER_ITEMS = len(pickle.load(open(ITEM_FILE, 'rb')))
NUMBER_MOVES = len(pickle.load(open(MOVE_FILE, 'rb')))
NUMBER_CLASSES = NUMBER_POKEMON + NUMBER_MOVES + 1 # number moves, number pokemon, megaevolve
STATUS_EFFECTS = set(['PARALYZED', 'POISONED', 'BADLY POISONED', 'BURNED', 'FROZEN', 'SLEEP'])
