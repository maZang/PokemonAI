from reinforcement.environment import Environment
from learner.approxqlearner import ApproxQLearner
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time


class PokemonShowdownConfig(object):
	'''
	Config for Pokemon showdown
	'''
	user='CS6700AI'
	password='HORSERADISHBACON'
	learner=ApproxQLearner


class PokemonShowdownConfigSelfPlay(object):
	user='CS6700AITest'
	password='HORSERADISHBACON'
	learner=ApproxQLearner


class PokemonShowdown(Environment):
	def __init__(self, config, driver):
		self.learner = config.learner
		self.driver = driver

	def getCurrentState(self):
		'''
		Gets the current state of the environment.
		'''
		pass

	def getActions(self, state=None):
		'''
		Returns the actions possible for the current state. If state=None, return all actions.
		'''
		pass

	def reset(self):
		'''
		Resets the environment to the start state
		'''
		pass

	def update(self, action):
		'''
		Updates the state based upon the current state and action. Returns the new state
		and a reward
		'''
		pass

	def isEndState(self):
		'''
		Checks if it is an end state, e.g. the episode is over
		'''
		pass

	def parseStateFromJSON(self, data):
		'''
		Parses the JSON printed from console.log.
		'''
		for pokemon in data["side"]["pokemon"]:
			species = pokemon["details"].split(',')[0]

			# Health is in the format "CurrHP/TotalHP", ex. "250/301".
			health = pokemon["condition"]

			# Active is true or false.
			active = pokemon["active"]

			# Moves is a list of strings.
			moves = pokemon["moves"]

			if "item" in pokemon:
				item = pokemon["item"]


DRIVERFOLDER = 'driver/chromedriver.exe'
BASEURL = 'http://play.pokemonshowdown.com/'

def login(driver, showdown_config):
	driver.get(BASEURL)
	time.sleep(0.5)
	driver.find_element(By.NAME, "login").click()
	time.sleep(0.5)
	driver.find_element(By.NAME, "username").clear()
	driver.find_element(By.NAME, "username").send_keys(showdown_config.user)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)
	driver.find_element(By.NAME, "password").clear()
	driver.find_element(By.NAME, "password").send_keys(showdown_config.password)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)

def challenge(driver1, driver2, showdown_config1, showdown_config2):
	time.sleep(0.5)
	driver1.find_element(By.NAME, "finduser").click()
	time.sleep(0.5)
	driver1.find_element(By.NAME, "data").clear()
	driver1.find_element(By.NAME, "data").send_keys(showdown_config2.user)
	driver1.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(0.5)
	driver1.find_element(By.NAME, "challenge").click()
	driver1.find_element(By.CSS_SELECTOR, 'button[class="select formatselect"]').click()
	driver1.find_element(By.CSS_SELECTOR, 'button[value="battlefactory"]').click()
	driver1.find_element(By.NAME, "makeChallenge").click()
	time.sleep(0.5)
	driver2.find_element(By.NAME, "acceptChallenge").click()
	time.sleep(0.5)
	driver1.find_element(By.CSS_SELECTOR, 'button[value="0"]').click()
	driver2.find_element(By.CSS_SELECTOR, 'button[value="0"]').click()
	time.sleep(0.5)

def analyzeLog(driver):
	data = driver.get_log('browser')
	print(data)

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself():
	showdown_config1 = PokemonShowdownConfig()
	showdown_config2 = PokemonShowdownConfigSelfPlay()
	options = Options()
	options.add_argument("--disable-notifications")
	options.add_argument("--mute-audio")
	driver1 = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=options)
	driver2 = webdriver.Chrome(executable_path=DRIVERFOLDER, chrome_options=options)
	driver1.implicitly_wait(30)
	driver2.implicitly_wait(30)
	login(driver1, showdown_config1)
	login(driver2, showdown_config2)
	challenge(driver1, driver2, showdown_config1, showdown_config2)
