# import the necessary packages
import cv2
import numpy as np
from picamera2 import Picamera2, controls
import argparse
import warnings
import datetime
import json
import time

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
    help="path to the JSON configuration file")
args = vars(ap.parse_args())

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
#client = None

'''# check to see if the Dropbox should be used
if conf["use_dropbox"]:
    # connect to dropbox and start the session authorization process
    client = dropbox.Dropbox(conf["dropbox_access_token"])
    print("[SUCCESS] dropbox account linked")'''

# initialize the camera and grab a reference to the raw camera capture
from pprint import *
cam = Picamera2()
#pprint(camera.sensor_modes)
#exit
height =480
width=640
config = cam.create_video_configuration(main={"format": 'XRGB8888',
                                              "size": (width, height)})
cam.configure(config)
resolution = tuple(conf["resolution"])
framerate = conf["fps"]
cam.set_controls({"FrameRate": framerate})
#picam2.video_configuration.controls.FrameRate = 25.0
#cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
cam.start()

#rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
#print(conf["camera_warmup_time"])
time.sleep(conf["camera_warmup_time"])

avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# capture frames from the camera
while True:
    time.sleep(1)
    frame = cam.capture_array()
    
    #cv2.imshow('f', frame)
    #cv2.waitKey(1)
    #print(frame.shape)
    
    # the timestamp and occupied/unoccupied text
    timestamp = datetime.datetime.now()
    text = "Unoccupied" 

    # resize the frame, convert it to grayscale, and blur it
    #frame = imutils.resize(frame, width=500)
    #width = 500
    #height = 480 * 640/500
    #print(width, height)
    #dim = (width, height)

    #frame = cv2.resize(frame, (_, 500), interpolation = cv2.INTER_AREA)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    # if the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        #rawCapture.truncate(0)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 
                           255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2) 
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, 
                            cv2.CHAIN_APPROX_SIMPLE)
    #cnts = imutils.grab_contours(cnts) # TODO
    #print("min_area", conf["min_area"])
    #print("cnts", cnts)
    #i = 0

    # loop over the contours
    for c in cnts:
        #print(i) 
        #i+=1
        #print("c", c)
        
        print("c in pixel %d" % cv2.contourArea(c))

        # if the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue

        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # check to see if the room is occupied
    if text == "Occupied":
        # check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
            # increment the motion counter
            motionCounter += 1

            # check to see if the number of frames with consistent motion is
            # high enough
            if motionCounter >= conf["min_motion_frames"]:
                # check to see if dropbox sohuld be used
                '''if conf["use_dropbox"]:
                    # write the image to temporary file
                    t = TempImage()
                    cv2.imwrite(t.pat, frame)   

                    # upload the image to Dropbox and cleanup the tempory image
                    print("[UPLOAD] {}".format(ts))
                    path = "/{base_path}/{timestamp}.jpg".format(
                        base_path=conf["dropbox_base_path"], timestamp=ts)
                    #client.files_upload(open(t.path, "rb").read(), path)
                    t.cleanup()'''

            # update the last uploaded timestamp and reset the motion
            # counter
            lastUploaded = timestamp
            motionCounter = 0

    # otherwise, the room is not occupied
    else:
        motionCounter = 0

    # check to see if the frames should be displayed to screen
    if conf["show_video"]:
        # display the security feed
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        # if the `q` key is pressed, break from the lop
        if key == ord("q"):
            break

    # clear the stream in preparation for the next frame
    #rawCapture.truncate(0)
