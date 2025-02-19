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
from picamera2 import Picamera2 #, Preview
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
FLAG_CAM 				= 	False
FLAG_DISPLAY 			= 	False
FLAG_DISPLAY_TEST 		= 	True
FLAG_CAM_TEST			= 	True

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
PIR_Outdoor_PIN2 		= 	23		# 
BUTTON_PIN 				=	24
# Parameters / Outputs
#DISPLAY_PIN 			= 	24		# not necessary if KNX is used!

# Initialize Inputs/Outputs
# input
pir_outdoor1 = 	Button(PIR_Outdoor_PIN1, 	pull_up=False, bounce_time=0.2)
pir_outdoor2 = 	Button(PIR_Outdoor_PIN2, 	pull_up=False, bounce_time=0.2)
pir_indoor1 = 	Button(PIR_Indoor_PIN1, 	pull_up=False, bounce_time=0.2)
pir_indoor2 = 	Button(PIR_Indoor_PIN2, 	pull_up=False, bounce_time=0.2)
button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.2)
# output
#display = Button(DISPLAY_PIN) # not necessary if KNX is used!

# =============================================================================
# Parameters
# =============================================================================
# Time last PIR sensor something
elapsed_time_pir = time.time() 				# value 0 to begin with?
detections_pir_in = [None] * 3			# save times of 3 detections
detections_pir_out = [None] * 3			# save times of 3 detections
last_detection_in = None
last_detection_out = None
print(detections_pir_in)

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
		print("Stop streaming server ...TODO")
		print("Stop streaming server ...")
		self.shutdown()
		#self.server_close()

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
		server.stop()
		thread.join()
	except:
		print("Exception raised in stop_video()!")

def turn_on_display():
	print("turn_on_display()")
	global FLAG_DISPLAY
	FLAG_DISPLAY = True
	#GPIO.setup(OUT_DISPLAY, GPIO.HIGH)									# Todo
	# TBD: Program KNX address (vs directly via relais) + NodeRED

def turn_off_display():
	print("turn_off_display()")
	FLAG_DISPLAY = False
	#GPIO.setup(OUT_DISPLAY, GPIO.LOW)									# Todo

def calc_delta_t(elapsed_time, dT=60, typ="", str=""):
	now = time.time()
	delta_t = now - elapsed_time
	#print("now", now, "seconds")
	#print("delta_t", delta_t, "seconds")
	if not round(delta_t) % 10:
		print("%s#2 %s %d s." % (typ, str, dT-delta_t))
	
	return True if delta_t > dT else False

def skip_detections(detections):
	detections[0] = detections[1]
	detections[1] = detections[2]
	detections[2] = None
	
	return detections

def fill_detections(detections, t):
	if detections[0] == None:
		detections[0] = t
	elif detections[1] == None:
		detections[1] = t
	elif detections[2] == None:	
		detections[2] = t
	
	return detections

def check_n_detects(timings):
	global CONST_N_DETECTS_in_T
	delta = timings[-1] - timings[0]
	#print("deltaT = %.1f" % round( delta ,1))
	
	return True if delta < CONST_N_DETECTS_in_T else False

# Callbacks
# Callbacks / DISPLAY
def increment_pir_in():
	global Step_Display, detections_pir_in, last_detection_in, FLAG_PRINT_ONCE_DISPLAY, elapsed_time_pir
	now = time.time()
	last_detection_in = now

	# Reset if any PIR gets a detection
	elapsed_time_pir = callback_pir_sensor()

	if Step_Display < 1:
		# INITIALIZE = new detection
		#detections = fill_detections(detections, now)
		if detections_pir_in[0] == None:
			detections_pir_in[0] = now
		elif detections_pir_in[1] == None:
			detections_pir_in[1] = now
		elif detections_pir_in[2] == None:	
			detections_pir_in[2] = now
		
			if check_n_detects(detections_pir_in) and not (None in detections_pir_in):
				# 3 detects < 8 secs & 3 timings --> Reset
				detections_pir_in = [None] * 3

				# Turn on display
				if Step_Display == 0:
					Step_Display += 1
					FLAG_PRINT_ONCE_DISPLAY = True
			else:
				# Remove 1 detection
				detections_pir_in = skip_detections(detections_pir_in)

# Callbacks / CAM
def increment_pir_out():
	global Step_Cam, detections_pir_out, last_detection_out, FLAG_PRINT_ONCE_CAM, elapsed_time_pir
	now = time.time()
	last_detection_out = now

	# Reset if any PIR gets a detection
	elapsed_time_pir = callback_pir_sensor()

	if Step_Cam < 1:
		# INITIALIZE
		if detections_pir_out[0] == None:
			detections_pir_out[0] = now
		elif detections_pir_out[1] == None:
			detections_pir_out[1] = now
		elif detections_pir_out[2] == None:	
			detections_pir_out[2] = now
		
			if check_n_detects(detections_pir_out) and not (None in detections_pir_out): #INCREMENT_PIR_INNER_INI
				# 3 detects < 8 secs & 3 timings --> Reset
				detections_pir_out = [None] * 3

				# Turn on display
				if Step_Cam == 0:
					Step_Cam += 1
					FLAG_PRINT_ONCE_CAM = True
			else:
				# Remove 1 detection
				detections_pir_out = skip_detections(detections_pir_out)

# Reset last motion detection
def callback_pir_sensor():
	#print("PIR: Motion detected!")
	return time.time()

# Console
def print_once_cam(string):
	global FLAG_PRINT_ONCE_CAM
	if FLAG_PRINT_ONCE_CAM:
		print("\n%s" % string)
	FLAG_PRINT_ONCE_CAM = False

def print_once_display(string):
	global FLAG_PRINT_ONCE_DISPLAY
	if FLAG_PRINT_ONCE_DISPLAY:
		print("\n%s" % string)
	FLAG_PRINT_ONCE_DISPLAY = False



# Testing

# Events
#button.when_pressed = schrittkette
pir_indoor1.when_pressed = increment_pir_in
pir_indoor2.when_pressed = increment_pir_in
pir_outdoor1.when_pressed = increment_pir_out
pir_outdoor2.when_pressed = increment_pir_out

# =============================================================================
# MAIN
# =============================================================================
def main():
	global Step_Cam, Step_Display
	global elapsed_time_pir
	global FLAG_PRINT_ONCE_CAM
	global FLAG_PRINT_ONCE_DISPLAY
	try:
		# cam outdoor & display indoor
		while True:
			time.sleep(1)

			# CAMERA
			if FLAG_CAM_TEST:
				if Step_Cam == 0:
					print_once_cam("Cam#0 - Init.")
					pass

				elif Step_Cam == 1:
					# Increment=Start if 3 detections in 3 seconds
					print_once_cam("Cam#1 - detect#3 = Start recording.")
					
					start_video()
					Step_Cam += 1

				elif Step_Cam == 2:
					t = 30
					print_once_cam("Cam#2 - Stop recording in %d s." % t)
					
					if calc_delta_t(elapsed_time_pir, t, "Cam", "- Stop recording in"):
						Step_Cam = 0
						stop_video()

			# DISPLAY
			if FLAG_DISPLAY_TEST:
				if Step_Display == 0:
					print_once_display("Display#0 - Init.")
					pass

				elif Step_Display == 1:
					# Increment=Start if 3 detections in 3 seconds
					print_once_display("Display#1 - turn ON.")
					turn_on_display()
					
					Step_Display += 1
					FLAG_PRINT_ONCE_DISPLAY = True

				elif Step_Display == 2:
					t = 60
					print_once_display("Display#2 will be turned OFF in %d s." % t)
										
					delta_t = calc_delta_t(elapsed_time_pir, t, "Display", "will be turned OFF in")
					if delta_t:
						Step_Display = 0
						turn_off_display()
	
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
	main()
