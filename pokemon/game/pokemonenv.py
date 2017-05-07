from reinforcement.environment import Environment
from learner.approxqlearner import ApproxQLearner
from selenium import webdriver
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


DRIVERFOLDER = 'driver/chromedriver.exe'
BASEURL = 'http://play.pokemonshowdown.com/'

def login(driver, showdown_config):
	driver.get(BASEURL)
	time.sleep(1)
	driver.find_element(By.NAME, "login").click()
	time.sleep(1)
	driver.find_element(By.NAME, "username").clear()
	time.sleep(1)
	driver.find_element(By.NAME, "username").send_keys(showdown_config.user)
	time.sleep(1)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(1)
	driver.find_element(By.NAME, "password").clear()
	time.sleep(1)
	driver.find_element(By.NAME, "password").send_keys(showdown_config.password)
	time.sleep(1)
	driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
	time.sleep(1)

def challenge(driver1, driver2, showdown_config1, showdown_config2):
	driver1.find_element(By.NAME, "finduser").click()
	time.sleep(1)
	driver1.find_element(By.NAME, "data").clear()
	time.sleep(1)
	driver1.find_element(By.NAME, "data").send_keys(showdown_config2.user)

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself():
	showdown_config1 = PokemonShowdownConfig()
	showdown_config2 = PokemonShowdownConfigSelfPlay()
	driver1 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	driver2 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver1, showdown_config1)
	login(driver2, showdown_config2)
	challenge(driver1, driver2, showdown_config1, showdown_config2)

