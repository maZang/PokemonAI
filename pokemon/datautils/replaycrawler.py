from bs4 import BeautifulSoup
import urllib
import urllib.request
import urllib.error
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

SEARCH_FORMAT = 'gen7randombattle'
BASEURL = 'https://replay.pokemonshowdown.com/'
SEARCHURL = BASEURL + 'search/?format=' + SEARCH_FORMAT
DATAFOLDER = 'data/replays'
DRIVERFOLDER = '../../driver/chromedriver.exe'

def crawl():
	try: 
		req = urllib.request.Request(SEARCHURL, headers={'User-Agent' : 'Magic Browser'})
		replays = urllib.request.urlopen(req)
		replays_soup = BeautifulSoup(replays, 'html.parser')
		driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
		for link in replays_soup.findAll('a', href=True):
			if SEARCH_FORMAT not in link['href']:
				continue
			driver.get(BASEURL + link['href'])

			delay = 3 # 3 seconds wait

			try:
				print("Start of try block")
				element_present = EC.presence_of_element_located((By.CLASS_NAME, "replayDownloadButton"))
				WebDriverWait(driver, delay).until(element_present)
			except TimeoutException:
				print("Page taking too long!")

			html = driver.page_source
			replay_soup = BeautifulSoup(html)
			for l in replay_soup.findAll('a', href=True):
				print(l)

			break
	except (urllib.error.HTTPError,urllib.error.URLError) as e:
		print(e.fp.read())

crawl()