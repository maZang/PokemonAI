POKE_DESCRIPTOR_SIZE = 7
POKE_META_SIZE = 1 # current health percentage
FIELD_META_SIZE = 0 # number of field status (e.g. weather) -- 0 for now
NON_EMBEDDING_DATA = 12 * POKE_META_SIZE + FIELD_META_SIZE
NUMBER_CLASSES = 10 # 4 options for each move, +5 options to switch Pokemon, +1 mega-evolve -- ALTERNATIVE, number_moves + 