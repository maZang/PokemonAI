import json
import pickle

DATAFILE = 'data/factory-sets.json'

OUTPUT_POKE_DICT = 'data/info/pokemon.p'
OUTPUT_MOVE_DICT = 'data/info/move.p'
OUTPUT_ITEM_DICT = 'data/info/item.p'


pokemon = set([])
moves = set([])
items = set([])

with open(DATAFILE, 'r') as datafile:
	data = json.load(datafile)

for tier in data:
	for poke in data[tier]:
		pokemon.add(poke)
		for set in data[tier][poke]['sets']:
			if 'item' in set:
				items.add(set['item'])
			if 'moves' in set:
				for move in set['moves']:
					moves.add(move[0])
pokemon_dict = {poke:(i+1) for i,poke in enumerate(pokemon)}
move_dict = {move:(i+1) for i,move in enumerate(moves)}
item_dict = {item:(i+1) for i,item in enumerate(items)}
for dict in [pokemon_dict,move_dict,item_dict]:
	dict['<UNK>'] = 0
with open(OUTPUT_POKE_DICT, 'wb') as f:
	pickle.dump(pokemon_dict, f)
with open(OUTPUT_MOVE_DICT, 'wb') as f:
	pickle.dump(move_dict, f)
with open(OUTPUT_ITEM_DICT, 'wb') as f:
	pickle.dump(item_dict, f)