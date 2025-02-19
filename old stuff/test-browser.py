import time
import subprocess

p = subprocess.Popen(["firefox", "http://192.168.178.142:8000/index.html"])
time.sleep(600)
p.kill()