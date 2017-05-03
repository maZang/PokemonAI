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

def bulk_search():
	try: 
		with open(DATAFOLDER + SEEN_GAMES, 'r') as f:
			seen_games = set([line.strip() for line in f])
		# set up options to download into data folder
		chromeOptions = webdriver.ChromeOptions()
		prefs = {'download.default_directory' : os.path.abspath(DATAFOLDER), 
				'directory_upgrade' : True,
				'extensions_to_open': ""}
		chromeOptions.add_experimental_option('prefs', prefs)
		driver = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=chromeOptions)
		driver.get(SEARCHURL)
		delay = 3
		try:
			for i in range(1000):
				element_present = EC.presence_of_element_located((By.NAME, "moreResults"))
				WebDriverWait(driver, delay).until(element_present)
				more_button = driver.find_element(By.NAME, 'moreResults')
				more_button.click()
		except:
			print("No more clicks")
		replays_soup = BeautifulSoup(driver.page_source, 'html.parser')
		for link in replays_soup.findAll('a', href=True):
			if SEARCH_FORMAT not in link['href'] or link['href'][1:] in seen_games:
				continue
			url = BASEURL + link['href'][1:] + '.log'
			logreq =  urllib.request.Request(url, headers={'User-Agent' : 'Magic Browser'})
			logpage = urllib.request.urlopen(logreq)
			with open(DATAFOLDER + link['href'][1:] + '.txt', 'wb') as f:
				f.write(logpage.read())
			seen_games.add(link['href'][1:])
		print(len(seen_games))
		with open(DATAFOLDER + SEEN_GAMES, 'w') as f:
			for game in seen_games:
				f.write(game + "\n")
	except (urllib.error.HTTPError,urllib.error.URLError) as e:
		print(e.fp.read())