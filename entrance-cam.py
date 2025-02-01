# Program to activate a camera via motion detectors and also turning on 
# a touch screen monitor to see which person is standing in front of the 
# entrance door.

# Import
# Import / System
import time
import datetime
import socket

# Import / GPIO PINs
import gpiozero as GPIO
from gpiozero import Button, LED

# Streaming 
import io
import logging
import socketserver
from http import server
from threading import Condition

# Import / Camera
USB_CAMERA = True
if USB_CAMERA:
	import cv2
else:
	from picamera2 import Picamera2#, Preview
	from picamera2.encoders import JpegEncoder, H264Encoder, Quality
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
Dummy_PIN = 			17		# 6
PIR_Outdoor_PIN = 		27		# 7
PIR_Indoor_PIN = 		22		# 8
BUTTON_PIN = 			23		# 8
# Parameters / Outputs
DISPLAY_PIN = 			24		# 9 # not necessary if KNX is used!

# Parameters / Flags
Video = 				False
Display = 				False
Step_Cam = 				0
Step_Display = 			0

# Parameters / Debugging and testing
flag_streaming = 		False # 0 = preview, 1 = vlc stream
FLAG_PRINT_ONCE_CAM		=	True
FLAG_PRINT_ONCE_DISPLAY	=	True

# Initialize Inputs/Outputs
# input
dummy = Button(Dummy_PIN, pull_up=False, bounce_time=0.2)
pir_outdoor = Button(PIR_Outdoor_PIN, pull_up=False, bounce_time=0.2)
pir_indoor = Button(PIR_Indoor_PIN, pull_up=False, bounce_time=0.2)
button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.2)
# output
display = Button(DISPLAY_PIN, pull_up=False, bounce_time=0.2) # not necessary if KNX is used!

# =============================================================================
# Camera setup
# =============================================================================
# Settings for image recording
if USB_CAMERA:
	cam = cv2.VideoCapture(0)
	cam.set(3,640) # set Width
	cam.set(4,480) # set Height       
	cv2.namedWindow("camera")
else:
	# Camera setup
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
'''

# Time last PIR sensor something
elapsed_time_pir = time.time() # value 0 to begin with?
elapsed_time_pir_outside = time.time()

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
	#picam2.stop_preview()

def turn_on_display():
	print("--> Turning display on!")
	Display = True
	#GPIO.setup(OUT_DISPLAY, GPIO.HIGH)									# Todo
	# TBD: Program KNX address (vs directly via relais) + NodeRED

def turn_off_display():
	print("--> Turning display off")
	Display = False
	#GPIO.setup(OUT_DISPLAY, GPIO.LOW)									# Todo

# Test gpiozero
#def pressed():
#    print("button was pressed")
#def released():
#    print("button was released")
def schrittkette():
	global Step_Cam
	if Step_Cam < 3:
		Step_Cam += 1
	else:
		Step_Cam = 0


def step_chain_cam(null):
	global Step_Cam, PRINT_ONCE_Cam
	if Step_Cam < 2:
		Step_Cam += 1
	else:
		Step_Cam = 0
	# Debug
	PRINT_ONCE_Cam = True

def time_delta(elapsed_time, dT=60):
	current_time = time.time()
	delta_t = current_time - elapsed_time
	#print("c", current_time, "seconds")
	#print("e", elapsed_time, "seconds")
	print("...", round(delta_t, 1), "seconds.")
	return True if delta_t > dT else False

# Callbacks
# Callbacks / CAM
def increment_pir_outdoor(null):
	callback_pir_sensor() # Reset last motion detection
	global Step_Cam, FLAG_PRINT_ONCE_CAM
	if Step_Cam < 2:
		Step_Cam += 1
		FLAG_PRINT_ONCE_CAM = True
	elif Step_Cam == 2:
		if time_delta(elapsed_time_pir_outside, 3):
			Step_Cam += 1
			FLAG_PRINT_ONCE_CAM = True
	# We want 3 detections in e.g. 3 seconds to turn on video
	# Get and save the time to compare with
	if Step_Cam == 0:
		callback_pir_sensor_first()
		FLAG_PRINT_ONCE_CAM = True

# Callbacks / DISPLAY
def increment_pir_indoor(null):
	callback_pir_sensor()
	global Step_Display, FLAG_PRINT_ONCE_DISPLAY
	if Step_Display < 3:
		Step_Display += 1
		FLAG_PRINT_ONCE_DISPLAY = True

# Reset last motion detection
def callback_pir_sensor():
	print("Motion detected!")
	global elapsed_time_pir
	elapsed_time_pir = time.time()

# Reset only with first detection
def callback_pir_sensor_first():
	print("Motion detected - Outside #1!")
	global elapsed_time_pir_outside
	elapsed_time_pir_outside = time.time()

# Console
def print_once_cam(string):
	global FLAG_PRINT_ONCE_CAM
	if FLAG_PRINT_ONCE_CAM:
		print(string)
	FLAG_PRINT_ONCE_CAM = False

def print_once_display(string):
	global FLAG_PRINT_ONCE_DISPLAY
	if FLAG_PRINT_ONCE_DISPLAY:
		print(string)
	FLAG_PRINT_ONCE_DISPLAY = False

# Events
#button.wait_for_press(schrittkette())
#button.when_pressed = pressed
#button.when_released = released
button.when_pressed = schrittkette
pir_outdoor.when_pressed = increment_pir_outdoor
pir_indoor.when_pressed = increment_pir_indoor

def main():
	try:
		global Step_Cam, Step_Display
		global elapsed_time_pir
		global FLAG_PRINT_ONCE_CAM, FLAG_PRINT_ONCE_DISPLAY
		
		# Set up and start the streaming server
		#address = ('', 8000)
		#server = StreamingServer(address, StreamingHandler)
		#server.serve_forever()
		
		# cam outdoor & display indoor
		while True:
			time.sleep(1)
		
			if USB_CAMERA:
				ret, frame = cam.read()
				if not ret:
					print("failed to grab frame")
				cv2.imshow("camera", frame)
				k = cv2.waitKey(1)
				if k != -1:
					break

			# CAMERA
			if Step_Cam == 0:
				print_once_cam("Cam#0 - Init.")
			elif Step_Cam == 1:
				print_once_cam("Cam#1 - detect#1.")
			elif Step_Cam == 2:
				print_once_cam("Cam#2 - detect#2.")
			elif Step_Cam == 3:
				print_once_cam("Cam#3 - detect#3 = Start recording.")
				start_video()
				FLAG_PRINT_ONCE_CAM = True
				# Increment=Start if 3 detections in 3 seconds
				Step_Cam += 1
			elif Step_Cam == 4:
				print_once_cam("Cam#4 - Stop recording in ...")
				if time_delta(elapsed_time_pir, 10):
					Step_Cam = 0
					stop_video()
	
			# DISPLAY
			if Step_Display == 0:
				print_once_display("Display#0 - Init.")
			elif Step_Display == 1:
				print_once_display("Display#1 - detect#1.")
			elif Step_Display == 2:
				print_once_display("Display#2 - detect#2.")
			elif Step_Display == 3:
				print_once_display("Display#3 - detect#3 = turn ON.")
				turn_on_display()
				FLAG_PRINT_ONCE_DISPLAY = True
				# Increment=Start if 3 detections in 3 seconds
				Step_Display += 1
			elif Step_Display == 4:
				print_once_display("Display#4 - Display will be turned OFF in ...")
				if time_delta(elapsed_time_pir, 60):
					turn_off_display()
					Step_Display == 0
	
	except KeyboardInterrupt:
		print("Abort!")
	finally:
		print("finished!")
		#GPIO.cleanup()
		#picam2.stop_recording()

if __name__ == "__main__":
	main()
