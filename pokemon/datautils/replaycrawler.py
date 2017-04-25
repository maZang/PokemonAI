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

SEARCH_FORMAT = 'gen7randombattle'
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
		# set up options to download into data folder
		chromeOptions = webdriver.ChromeOptions()
		prefs = {'download.default_directory' : os.path.abspath(DATAFOLDER), 
				'directory_upgrade' : True,
				'extensions_to_open': ""}
		chromeOptions.add_experimental_option('prefs', prefs)
		driver = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=chromeOptions)
		for link in replays_soup.findAll('a', href=True):
			if SEARCH_FORMAT not in link['href'] or link['href'] in seen_games:
				continue
			driver.get(BASEURL + link['href'][1:])
			print(BASEURL + link['href'][1:])

			delay = 3 # 3 seconds wait

			try:
				element_present = EC.presence_of_element_located((By.CLASS_NAME, "replayDownloadButton"))
				WebDriverWait(driver, delay).until(element_present)
				dl_button = driver.find_elements_by_class_name('replayDownloadButton')
				assert(len(dl_button) == 1)
				dl_button[0].click()
				seen_games.add(link['href'])
			except TimeoutException:
				print("Page taking too long!")
		with open(DATAFOLDER + SEEN_GAMES, 'w') as f:
			for game in seen_games:
				f.write(game + "\n")
	except (urllib.error.HTTPError,urllib.error.URLError) as e:
		print(e.fp.read())
