from bs4 import BeautifulSoup
import urllib
import urllib.request
import urllib.error
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os 
import time
from datetime import datetime

SEARCH_FORMAT = 'battlefactory'
BASEURL = 'https://replay.pokemonshowdown.com/'
SEARCHURL = BASEURL + 'search/?format=' + SEARCH_FORMAT
DATAFOLDER = 'data/replays/'
SEEN_GAMES = 'replay_games.txt'
DRIVERFOLDER = 'driver/chromedriver.exe'

def crawl():
	try: 
		with open(DATAFOLDER + SEEN_GAMES, 'r') as f:
			seen_games = set([line.strip() for line in f])
		req = urllib.request.Request(SEARCHURL, headers={'User-Agent' : 'Magic Browser'})
		replays = urllib.request.urlopen(req)
		replays_soup = BeautifulSoup(replays, 'html.parser')
		for link in replays_soup.findAll('a', href=True):
			if SEARCH_FORMAT not in link['href'] or link['href'][1:] in seen_games:
				continue
			url = BASEURL + link['href'][1:] + '.log'
			logreq =  urllib.request.Request(url, headers={'User-Agent' : 'Magic Browser'})
			logpage = urllib.request.urlopen(logreq)
			with open(DATAFOLDER + link['href'][1:] + '.txt', 'wb') as f:
				f.write(logpage.read())
			seen_games.add(link['href'][1:])
		with open(DATAFOLDER + SEEN_GAMES, 'w') as f:
			for game in seen_games:
				f.write(game + "\n")
			
	except (urllib.error.HTTPError,urllib.error.URLError) as e:
		print(e.fp.read())

def spiderman():
	while True:
		print('Crawling-----------------------------------------------------------')
		crawl()
		print('Sleeping for 30 minutes--------------------------------------------')
		print('Current Time: ' + str(datetime.now()))
		time.sleep(30 * 60)
		print('Woke up at: ' + str(datetime.now()))

