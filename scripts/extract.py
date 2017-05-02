import json
import pickle

DATAFILE = 'data/factory-sets.json'

OUTPUT_POKE_DICT = 'data/info/pokemon.p'
OUTPUT_MOVE_DICT = 'data/info/move.p'
OUTPUT_ITEM_DICT = 'data/info/item.p'

OUTPUT_POKE_DICT2 = 'data/info/pokemon2.p'
OUTPUT_MOVE_DICT2 = 'data/info/move2.p'
OUTPUT_ITEM_DICT2 = 'data/info/item2.p'


pokemon = set([])
moves = set([])
items = set([])

with open(DATAFILE, 'r') as datafile:
	data = json.load(datafile)

for tier in data:
	for poke in data[tier]:
		for set in data[tier][poke]['sets']:
			if 'species' in set:
				pokemon.add(set['species'])
			if 'item' in set:
				if 'ite' in set['item'][-3:] and set['item'] != 'Eviolite':
					pokemon.add(set['species'] + '-Mega')
				if 'ite X' in set['item'][-5:] or 'ite Y' in set['item'][-5:]:
					pokemon.add(set['species'] + '-Mega-X')
					pokemon.add(set['species'] + '-Mega-Y')
				items.add(set['item'])
			if 'moves' in set:
				for move in set['moves']:
					moves.update(move)

pokemon.add(u'Groudon-Primal')
pokemon.add(u'Kyogre-Primal')
pokemon_dict = {poke:(i+1) for i,poke in enumerate(pokemon)}
pokemon_dict['<UNK>'] = 0
move_dict = {move:(i+1+len(pokemon_dict)) for i,move in enumerate(moves)}
move_dict['<UNK>'] = len(pokemon_dict)
item_dict = {item:(i+1+len(pokemon_dict)+len(move_dict)) for i,item in enumerate(items)}
item_dict['<UNK>'] = len(pokemon_dict) + len(move_dict)
with open(OUTPUT_POKE_DICT, 'wb') as f:
	pickle.dump(pokemon_dict, f)
with open(OUTPUT_MOVE_DICT, 'wb') as f:
	pickle.dump(move_dict, f)
with open(OUTPUT_ITEM_DICT, 'wb') as f:
	pickle.dump(item_dict, f)
# for python 2
with open(OUTPUT_POKE_DICT2, 'wb') as f:
	pickle.dump(pokemon_dict, f, protocol=2)
with open(OUTPUT_MOVE_DICT2, 'wb') as f:
	pickle.dump(move_dict, f, protocol=2)
with open(OUTPUT_ITEM_DICT2, 'wb') as f:
	pickle.dump(item_dict, f, protocol=2)