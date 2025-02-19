#!/usr/bin/python3

import time
from selenium import webdriver

url = 'http://192.168.178.142:8000/index.html'
waiting_duration_before_refresh = 5

driver = webdriver.Firefox()
driver.get(url)

assert "Example" in driver.title

time.sleep(waiting_duration_before_refresh)
driver.refresh()