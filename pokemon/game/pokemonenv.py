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

	def __init__(self, config):
		self.learner = config.learner

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

def runPokemonShowdown():
	showdown_config = PokemonShowdownConfig()
	driver = webdriver.Chrome(executable_path=DRIVERFOLDER)
	login(driver, showdown_config)

def runAgainstItself():
	showdown_config1 = PokemonShowdownConfig()
	showdown_config2 = PokemonShowdownConfig()
	driver1 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	driver2 = webdriver.Chrome(executable_path=DRIVERFOLDER)
	