#-----------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#-----------------------------------------------------------------------------------------

# Setup logging first
import logging.handlers
import logging, sys
from flask import Response, Flask, render_template
	
# initialize a flask object
app = Flask(__name__)

if __name__ == "main":
	# Running directly so setup custom logging
	logging.basicConfig(
		level=logging.INFO,
		format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s] %(message)s",
		datefmt="%d/%b/%Y %H:%M:%S",
		stream=sys.stdout)
else:
	# Running under gunicorn so use their logger
	gunicorn_logger = logging.getLogger('gunicorn.error')
	rootLogger = logging.getLogger();
	rootLogger.handlers = gunicorn_logger.handlers
	rootLogger.setLevel(gunicorn_logger.level)

# import the necessary packages
import threading
import datetime
import imutils
import time
import cv2
from motion_detector.motiondetector import MotionDetector

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None
debugFrame = None
lock = threading.Lock()

# initialize the video stream and allow the camera sensor to
# warmup
#vs = VideoStream(usePiCamera=1).start()
#vs = VideoStream(src=0).start()
vs = cv2.VideoCapture("/var/lib/vids/testing.MOV")
time.sleep(2.0)

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

def detect_motion():
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame, debugFrame, lock

	ret, frame1 = vs.read()
	if not ret:
		return;

	fps = int(vs.get(cv2.CAP_PROP_FPS))
	app.logger.info("Video playing at %s fps", fps)

	detector = MotionDetector(fps, "/home/myuser/data")
	detector.loadFirstFrame(frame1=frame1)

    # loop over frames from the video stream
	while True:
		ret, frame2 = vs.read()
		if not ret:
			break

		output, debug = detector.process(frame=frame2)

		# acquire the lock, set the output frame, and release the
		# lock
		with lock:
			if output is not None:
				outputFrame = output.copy()
			if debug is not None:
				debugFrame = debug.copy()

		#time.sleep(0.05)

def generate():
	# grab global references to the output frame and lock variables
	global outputFrame, lock
	
	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop
			if outputFrame is None:
				continue
			
			# encode the frame in JPEG format
			try:
				(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
			except:
				app.logger.exception("Failed to encode image")
				continue
			
			# ensure the frame was successfully encoded
			if not flag:
				continue
			
		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')
	
def generate_debug():
	# grab global references to the output frame and lock variables
	global debugFrame, lock
	
	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop
			if debugFrame is None:
				continue
			
			# encode the frame in JPEG format
			try:
				(flag, encodedImage) = cv2.imencode(".jpg", debugFrame)
			except:
				app.logger.exception("Failed to encode image")
				continue
			
			# ensure the frame was successfully encoded
			if not flag:
				continue
			
		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/debug_feed")
def debug_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate_debug(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

# start a thread that will perform motion detection
t = threading.Thread(target=detect_motion, args=(), daemon=True)
t.start()

# Used for starting locally. Under gunircorn this won't get hit
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)