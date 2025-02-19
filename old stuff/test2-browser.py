from selenium import webdriver
import time
import urllib
import urllib2
    
refreshrate = 3

driver = webdriver.Firefox()
driver.get("http://192.168.178.142:8000/index.html")

while True:
    time.sleep(refreshrate)
    driver.refresh()