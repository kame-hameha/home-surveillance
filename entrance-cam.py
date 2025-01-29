# Program to activate a camera via motion detectors and also turning on 
# a touch screen monitor to see which person is standing in front of the 
# entrance door.

# Import
# Import / System
import time
import datetime
import socket

# Import / GPIO
import RPi.GPIO as GPIO

# Streaming 
import io
import logging
import socketserver
from http import server
from threading import Condition

# Import / Camera
from picamera2 import Picamera2#, Preview
from picamera2.encoders import JpegEncoder#, H264Encoder, Quality
from picamera2.outputs import FileOutput

# HTML page for the MJPEG streaming demo
PAGE = """\
<html>
<head>
<title>RaspberryTips Pi Cam Stream</title>
</head>
<body>
<h1>Raspberry Tips Pi Camera Live Stream Demo</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

# Parameters
# Parameters / Inputs	Physical#
Dummy = 		17			# 6
PIR_Outdoor = 	27			# 7
PIR_Indoor = 	22			# 8

IN_BUTTON = 	23			# 8

# Parameters / Outputs
OUT_DISPLAY = 	24			# 9

# Parameters / Flags
Video = False
Display = False
Step_Cam = 0
Step_Display = 0

# Parameters / Debugging and testing
flag_streaming = 		False # 0 = preview, 1 = vlc stream
PRINT_ONCE = 			True
#PRINT_ONCE_Cam = 		True
#PRINT_ONCE_Display = 	True

# GPIO setup
GPIO.setmode(GPIO.BCM)     					# set up BCM GPIO numbering  
GPIO.setup(IN_BUTTON, GPIO.IN)
#GPIO.setup(PIR_OutdoorNear, GPIO.IN)		# Jumper for 1 s triggers
GPIO.setup(PIR_Outdoor, GPIO.IN)  
GPIO.setup(PIR_Indoor, GPIO.IN)
GPIO.setup(OUT_DISPLAY, GPIO.OUT) 

# Camera setup
'''
picam2 = Picamera2()
video_config = picam2.create_video_configuration(
		buffer_count=1, 
		encode="main", 
		queue=False, 
		main={"size": (1536, 864)}, 
		lores={"size": (320, 240)}) 
picam2.configure(video_config)
encoder = H264Encoder(bitrate=10000000, iperiod=1)
output_path = "/home/pi/Desktop/"
output = ".h264"
REC_TIME = 30
'''

# Class to handle streaming output
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# Class to handle HTTP requests
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Redirect root path to index.html
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            # Serve the HTML page
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            # Set up MJPEG streaming
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            # Handle 404 Not Found
            self.send_error(404)
            self.end_headers()

# Class to handle streaming server
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Create Picamera2 instance and configure it
picam2 = Picamera2()
video_config = picam2.create_video_configuration(
		buffer_count=1, 
		encode="main", 
		queue=False, 
		main={"size": (1280, 720)})
picam2.configure(video_config)
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

# Time last PIR sensor something
elapsed_time = time.time()

# Callbacks
# Functions / Methods
def start_video():
	print("Start recording ...")
	Video = True
	now = datetime.datetime.now()
	date = str(now.year) + "-" + str(now.month) + "-" + \
		   str(now.day) + "_" + str(now.hour) + ":" + \
		   str(now.minute) + ":" + str(now.second)
	'''
	picam2.start_preview(Preview.QTGL)
	picam2.start_recording(encoder, output_path + date + output) # second time error
	'''
	#time.sleep(REC_TIME)

def stop_video():
	# Use this instead of time.pause possible?
	Video = False
	
	#picam2.close()
	picam2.stop_preview()

def turn_on_display():
	print("--> Turning display on!")
	Display = True
	#GPIO.setup(OUT_DISPLAY, GPIO.HIGH)									# Todo
	# TBD: Program KNX address (vs directly via relais) + NodeRED

def turn_off_display():
	print("--> Turning display off")
	Display = False
	#GPIO.setup(OUT_DISPLAY, GPIO.LOW)									# Todo

'''
def schrittkette(null):
	global Step_Cam
	if Step_Cam < 2:
		Step_Cam += 1
	else:
		Step_Cam = 0
'''
'''
def step_chain_cam(null):
	global Step_Cam, PRINT_ONCE_Cam
	if Step_Cam < 2:
		Step_Cam += 1
	else:
		Step_Cam = 0
	# Debug
	PRINT_ONCE_Cam = True
'''
def no_detection_in_deltat(DELTA_T=60):
	global elapsed_time
	current_time = time.time()
	delta_t = current_time - elapsed_time
	#print("c", current_time, "seconds")
	#print("e", elapsed_time, "seconds")
	print("...", round(delta_t, 1), "seconds.")
	if delta_t > DELTA_T:
		return 1
	else:
		return 0

# Callbacks
# Callbacks / CAM
def callback_pir_outdoor(null):
	callback_pir_sensor() # Reset last motion detection
	global Step_Cam
	if Step_Cam == 0:
		Step_Cam += 1

# Callbacks / DISPLAY
def callback_pir_indoor(null):
	callback_pir_sensor()
	global Step_Display
	if Step_Display == 0:
		Step_Display += 1

# Reset last motion detection
def callback_pir_sensor():
	print("Motion detected!")
	global elapsed_time
	elapsed_time = time.time()

# Console
def print_once(string):
	global FLAG_PRINT_ONCE
	if PRINT_ONCE:
		print(str(string))
	FLAG_PRINT_ONCE = False

# Events
'''
GPIO.add_event_detect(IN_BUTTON, 			# TESTING			
					  GPIO.RISING, 
					  callback=step_chain_cam,
					  bouncetime=200)
'''

GPIO.add_event_detect(PIR_Outdoor, 					
					  GPIO.RISING, 
					  callback=callback_pir_outdoor,
					  bouncetime=200)

GPIO.add_event_detect(PIR_Indoor, 						
					  GPIO.RISING, 
					  callback=callback_pir_indoor,
					  bouncetime=200)

def main():
	try:
		# Set up and start the streaming server
		address = ('', 8000)
		server = StreamingServer(address, StreamingHandler)
		server.serve_forever()
		
		# cam outdoor & display indoor
		while True:
			time.sleep(1)
			global Step_Cam, Step_Display
			print(Step_Cam)
			# CAMERA
			if Step_Cam == 0:
				print_once("Cam #0 - Init.")
			elif Step_Cam == 1:
				print_once("Cam #1 - Start recording.")
				start_video()
				Step_Cam += 1
			elif Step_Cam == 2:
				print_once("Cam #2 - Stop recording.")
				if no_detection_in_deltat(10):
					Step_Cam = 0
					stop_video()
					
					
			# DISPLAY
			if Step_Display:
				print_once("Display #0 - Init.")
			elif Step_Display == 1:
				print_once("Display #1 - ON.")
				turn_on_display()
				Step_Display += 1
			elif Step_Display == 2:
				print_once("Display #2 - Display will be turned OFF in ...")
				if no_detection_in_deltat(60):
					turn_off_display()
					Step_Display == 0

	except KeyboardInterrupt:
		print("Abort!")
	finally:
		print("GPIO cleanup!")
		GPIO.cleanup()
		picam2.stop_recording()

if __name__ == "__main__":
	main()
