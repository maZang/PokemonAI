import pickle

POKEMON_FILE = 'data/info/pokemon2.p'
ITEM_FILE = 'data/info/item2.p'
MOVE_FILE = 'data/info/move2.p'
POKE_DESCRIPTOR_SIZE = 7
POKE_META_SIZE = 1 # current health percentage
FIELD_META_SIZE = 0 # number of field status (e.g. weather) -- 0 for now
NON_EMBEDDING_DATA = 12 * POKE_META_SIZE + FIELD_META_SIZE
POKEMON_LIST = pickle.load(open(POKEMON_FILE, 'rb'))
ITEM_LIST = pickle.load(open(ITEM_FILE, 'rb'))
MOVE_LIST = pickle.load(open(MOVE_FILE, 'rb'))
NUMBER_POKEMON = len(POKEMON_LIST)
NUMBER_ITEMS = len(ITEM_LIST)
NUMBER_MOVES = len(MOVE_LIST)
NUMBER_CLASSES = NUMBER_POKEMON + NUMBER_MOVES + 1 # number moves, number pokemon, megaevolve
STATUS_EFFECTS = set(['PARALYZED', 'POISONED', 'BADLY POISONED', 'BURNED', 'FROZEN', 'SLEEP'])
UNK = '<UNK>'
DATA_TYPES = ["TRAINING", "VALIDATION", "TESTING"]
