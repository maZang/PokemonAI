import pickle

POKEMON_FILE = 'data/info/pokemon2.p'
ITEM_FILE = 'data/info/item2.p'
MOVE_FILE = 'data/info/move2.p'
ITEM_ENV_FILE = 'data/info/item_env.p'
MOVE_ENV_FILE = 'data/info/move_env.p'
# Pokemon ID, Move ID x4, Item ID, Status ID
POKE_DESCRIPTOR_SIZE = 7
POKE_META_SIZE = 1 # current health percentage
MAX_ACTIONS = 10
NUM_POKE = 12
NON_EMBEDDING_DATA = NUM_POKE * POKE_META_SIZE
POKEMON_LIST = pickle.load(open(POKEMON_FILE, 'rb'))
ITEM_LIST = pickle.load(open(ITEM_FILE, 'rb'))
MOVE_LIST = pickle.load(open(MOVE_FILE, 'rb'))
ITEM_ENV_LIST = pickle.load(open(ITEM_ENV_FILE, 'rb'))
MOVE_ENV_LIST = pickle.load(open(MOVE_ENV_FILE, 'rb'))
REV_POKEMON_LIST = {i:k for k, i in POKEMON_LIST.items()}
REV_MOVE_LIST = {i:k for k, i in MOVE_LIST.items()}
NUMBER_POKEMON = len(POKEMON_LIST)
NUMBER_ITEMS = len(ITEM_LIST)
NUMBER_MOVES = len(MOVE_LIST)
LAST_MOVE_DATA = 2
NUMBER_CLASSES = NUMBER_POKEMON + NUMBER_MOVES # number moves, number pokemon
STATUS_EFFECTS = set(['NONE', 'PARALYZED', 'POISONED', 'BADLY_POISONED', 'BURNED', 'FROZEN', 'SLEEP'])
STATUS_IDS = {status : (i + NUMBER_POKEMON + NUMBER_ITEMS + NUMBER_MOVES) for i,status in enumerate(STATUS_EFFECTS)}
UNK = '<UNK>'
DATA_TYPES = ["TRAINING", "VALIDATION", "TESTING"]