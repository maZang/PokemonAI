from bs4 import BeautifulSoup
import urllib
import urllib.request
import urllib.error
from selenium import webdriver

SEARCH_FORMAT = 'gen7randombattle'
BASEURL = 'https://replay.pokemonshowdown.com/'
SEARCHURL = BASEURL + 'search/?format=' + SEARCH_FORMAT
DATAFOLDER = 'data/replays'
DRIVERFOLDER = 'driver/chromedriver.exe'

def crawl():
	try: 
		req = urllib.request.Request(SEARCHURL, headers={'User-Agent' : 'Magic Browser'})
		replays = urllib.request.urlopen(req)
		replays_soup = BeautifulSoup(replays, 'html.parser')
		driver = webdriver.Chrome(DRIVERFOLDER)
		for link in replays_soup.findAll('a', href=True):
			if SEARCH_FORMAT not in link['href']:
				continue
			driver.get(BASEURL + link['href'])
			print(driver.page_source)
			print('done')
			break
	except (urllib.error.HTTPError,urllib.error.URLError) as e:
		print(e.fp.read())