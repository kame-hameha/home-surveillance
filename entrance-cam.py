#! /usr/bin/python3
# Program to activate a camera via motion detectors and also turning on 
# a touch screen monitor to see which person is standing in front of the 
# entrance door.

# Import
# Import / System
import time
import asyncio
import datetime
import socket
import threading

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
from picamera2 import Picamera2#, Preview
from picamera2.encoders import JpegEncoder, H264Encoder, MJPEGEncoder, Quality
from picamera2.outputs import FileOutput, FfmpegOutput, CircularOutput

# =============================================================================
# Homepage to visualize stream in a browser
# =============================================================================
# HTML page for the MJPEG streaming demo
PAGE = """\
<html>
<head>
<title>picamera2 MJPEG streaming demo</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="1280" height="960" />
</body>
</html>
"""

# Parameters / Flags
Step_Cam 				= 	0
Step_Display 			= 	0
FLAG_CAM 				= 	True
FLAG_DISPLAY 			= 	False

# Parameters / Debugging and testing
flag_streaming 			=	False			# 0 = preview, 1 = vlc stream
FLAG_PRINT_ONCE_CAM		=	True
FLAG_PRINT_ONCE_DISPLAY	=	True
CONST_N_DETECTS_in_T	= 	8.0				# seconds
INCREMENT_PIR_INNER_INI = 	0

# =============================================================================
# GPIO
# =============================================================================
# Parameters
# Parameters / Inputs	Physical#
PIR_Outdoor_PIN1 		= 	17		# 6
PIR_Indoor_PIN1 		= 	27		# 7
PIR_Indoor_PIN2 		= 	22		# 8
#PIR_Outdoor_PIN2 		= 	23		# 
BUTTON_PIN 				=	23
# Parameters / Outputs
#DISPLAY_PIN 			= 	24		# not necessary if KNX is used!

# Initialize Inputs/Outputs
# input
pir_outdoor1 = Button(PIR_Outdoor_PIN1, pull_up=False, bounce_time=0.2)
#pir_outdoor2 = Button(PIR_Outdoor_PIN2, pull_up=False, bounce_time=0.2)
pir_indoor1 = Button(PIR_Indoor_PIN1, pull_up=False, bounce_time=0.2)
pir_indoor2 = Button(PIR_Indoor_PIN2, pull_up=False, bounce_time=0.2)
button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.2)
# output
#display = Button(DISPLAY_PIN) # not necessary if KNX is used!

# =============================================================================
# Parameters
# =============================================================================
# Time last PIR sensor something
elapsed_time_pir = time.time() 				# value 0 to begin with?
elapsed_time_pir_outside = time.time() 		# save times of first 2 detections
elapsed_time_pir_inner = [None] * 3			# save times of first 2 detections
elapsed_time_pir_outer = [None] * 3			# save times of first 2 detections
#elapsed_time_pir_in = [0, 1, 2, 3] 		# save times of first 2 detections

# =============================================================================
# Streaming setup
# =============================================================================
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
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
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
            self.send_error(404)
            self.end_headers()

# Class to handle streaming server
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
	allow_reuse_address = True
	daemon_threads = True
	
	def run(self):
		print("Start streaming server ...")
		self.serve_forever()
	def stop(self):
		print("Stop streaming server ...")
		self.server_close()
		#self.shutdown

# =============================================================================
# Camera setup
# =============================================================================
output_path = "/home/pi/Desktop/"
file_type = ".h264" # ".h264" / ".mp4"

# Create Picamera2 instance and configure it
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (1920, 1080)})
#video_config = picam2.create_video_configuration(main={"size": (1280, 720)})

#video_config = picam2.create_video_configuration(main={"size": (1280, 720), "format": "RGB888"}, lores={"size": lsize, "format": "YUV420"})
'''video_config = picam2.create_video_configuration(
		buffer_count=1, 
		encode="main", 
		queue=False, 
		main={"size": (1920, 1080)})'''
picam2.configure(video_config)
output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

# =============================================================================
# Set up streaming server object to start and stop streaming
# =============================================================================
address = ('', 8000)
server = StreamingServer(address, StreamingHandler)
thread = None

# Callbacks
# Functions / Methods
#async def start_video():
def start_video():
	global server
	global thread
	print("Start video ...")

	'''now = datetime.datetime.now()
	date = str(now.year) + "-" + str(now.month) + "-" + \
		   str(now.day) + "_" + str(now.hour) + ":" + \
		   str(now.minute) + ":" + str(now.second)'''
	
	try:
		#server = StreamingServer(address, StreamingHandler)
		#server.serve_forever()
		thread = threading.Thread(None, server.run)
		thread.start()
		#server.run()
	except:
		print("Except in in start _video() at server.run()!")

def stop_video():
	global server
	global thread
	print("Stop video ...")

	try:
		#server.stop()
		server.shutdown()
		thread.join()
		#picam2.stop_recording()
	except:
		print("Exception raised in stop_video at stop_recording!")

def turn_on_display():
	print("Turning display on.")
	#GPIO.setup(OUT_DISPLAY, GPIO.HIGH)									# Todo
	# TBD: Program KNX address (vs directly via relais) + NodeRED

def turn_off_display():
	print("Turning display off.")
	#GPIO.setup(OUT_DISPLAY, GPIO.LOW)									# Todo

def time_delta(elapsed_time, dT=60):
	now = time.time()
	delta_t = now - elapsed_time
	#print("c", current_time, "seconds")
	#print("e", elapsed_time, "seconds")
	print("... dT =", round(delta_t, 1), "seconds.")
	return True if delta_t > dT else False

def reset_detections(t):
	# todo
	return time

def check_n_detects(timings):
	global elapsed_time_pir_inner, CONST_N_DETECTS_in_T
	return True if (elapsed_time_pir_inner[-1] - elapsed_time_pir_inner[0]) < CONST_N_DETECTS_in_T else False

# Callbacks
# Callbacks / CAM
def increment_pir_inner(null):
	#callback_pir_sensor() # Reset last motion detection
	global Step_Cam, elapsed_time_pir_inner
	global FLAG_PRINT_ONCE_CAM, INCREMENT_PIR_INNER_INI

	now = time.time()
	
	print("increment_pir_inner")

	# INITIALIZE
	if elapsed_time_pir_inner[0] == None:
		elapsed_time_pir_inner[0] = now
		#INCREMENT_PIR_INNER_INI += 1
	elif elapsed_time_pir_inner[1] == None:
		elapsed_time_pir_inner[1] = now
		#INCREMENT_PIR_INNER_INI += 1
	elif elapsed_time_pir_inner[2] == None:	
		elapsed_time_pir_inner[2] = now
		#INCREMENT_PIR_INNER_INI += 1
	else:
		elapsed_time_pir_inner[0] = elapsed_time_pir_inner[1]
		elapsed_time_pir_inner[1] = elapsed_time_pir_inner[2]
		elapsed_time_pir_inner[2] = now

	print("elapsed_time_pir_inner", elapsed_time_pir_inner)

	if check_n_detects and not (None in elapsed_time_pir_inner): #INCREMENT_PIR_INNER_INI
		# 3 detects < 8 secs & 3 timings --> Reset
		elapsed_time_pir_inner = [None] * 3
		#elapsed_time_pir_inner[0] = now
	else:
		# Remove first and set last one to None for nect detection
		elapsed_time_pir_inner[0] = elapsed_time_pir_inner[1]
		elapsed_time_pir_inner[1] = elapsed_time_pir_inner[2]
		elapsed_time_pir_inner[2] = None

	# Turn on display
	if Step_Cam == 1:
		Step_Cam += 1

	FLAG_PRINT_ONCE_CAM = True

# Callbacks / DISPLAY
def increment_pir_outer(null):
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



# Testing
'''t = time.time()

def test_pir(null):
	global t
	print("test pir %f" % (time.time() - t))'''

'''def schrittkette(null):
	global Step_Cam
	print("Step_Cam", Step_Cam)

	if Step_Cam < 4:
		Step_Cam += 1
	#else:
	#	Step_Cam = 0
	FLAG_PRINT_ONCE_CAM = True'''

# Events
#button.when_pressed = schrittkette
#pir_outdoor.when_pressed = increment_pir_outdoor
#pir_indoor.when_pressed = increment_pir_indoor

pir_indoor1.when_pressed = increment_pir_inner
pir_indoor2.when_pressed = increment_pir_inner

#async def main():
def main():
	try:
		global Step_Cam, Step_Display
		global elapsed_time_pir
		global FLAG_PRINT_ONCE_CAM
		global FLAG_PRINT_ONCE_DISPLAY
		
		# cam outdoor & display indoor
		while True:
			#await asyncio.sleep(0.1)
			time.sleep(1)

			# CAMERA
			if FLAG_CAM:
				if Step_Cam == 0:
					print_once_cam("Cam#0 - Init.")
					pass
				elif Step_Cam == 1:
					print_once_cam("Cam#1 - detect#3 = Start recording.")
					
					start_video()
					#await start_video()
					# Increment=Start if 3 detections in 3 seconds
					Step_Cam += 1 # ???	
				#elif Step_Cam == 2:
				#	pass
				#elif Step_Cam == 3:
				#	pass
				elif Step_Cam == 2:
					print_once_cam("Cam#2 - Stop recording in ...")
					
					if time_delta(elapsed_time_pir, 30):
						Step_Cam = 0
						stop_video()

			# DISPLAY
			if FLAG_DISPLAY:
				if Step_Display == 0:
					print_once_display("Display#0 - Init.")
					pass
				elif Step_Display == 1:
					print_once_display("Display#1 - turn ON.")
					turn_on_display()
					FLAG_PRINT_ONCE_DISPLAY = True
					# Increment=Start if 3 detections in 3 seconds
					Step_Display += 1			
				elif Step_Display == 2:
					print_once_display("Display#2 - will be turned OFF in ...")
					if time_delta(elapsed_time_pir, 60):
						Step_Display = 0
						turn_off_display()
				#elif Step_Display == 3:
				#elif Step_Display == 4:
			
	except KeyboardInterrupt:
		print("Abort!")
	finally:
		print("Stop recording")
		picam2.stop_recording()
		'''
		if USB_CAMERA:
			cv2.imwrite('/home/pi/Desktop/testimage.jpg', image)
			cam.release()
			cv2.destroyAllWindows()
		else:
			picam2.stop_recording()
			'''
		print("finished!")

if __name__ == "__main__":
	#asyncio.run(main())
	main()
