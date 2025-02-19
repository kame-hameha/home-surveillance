from selenium import webdriver


chrome_version = webdriver.chrome_version()
print(chrome_version)

#driver = webdriver.Chrome(ChromeDriverManager().install())
#browser= webdriver.Chrome(executable_path='/home/pi/ki-project/my_virtual_env/lib/python3.11/site-packages/selenium/webdriver/chrome/webdriver.py')

driver = webdriver.Chrome()
driver.get("http://www.google.com")