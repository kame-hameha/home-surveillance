import webbrowser
import pyautogui
from time import sleep

url = 'http://192.168.178.142:8000/index.html'
webbrowser.get('chromium').open(url)

while True:
    sleep(5)
    pyautogui.hotkey('f5')
