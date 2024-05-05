#-----------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#-----------------------------------------------------------------------------------------

# Setup logging first
import logging, sys

if __name__ == "main":
	# Running directly so setup custom logging
	logging.basicConfig(
		level=logging.INFO,
		format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s] %(message)s",
		datefmt="%d/%b/%Y %H:%M:%S",
		stream=sys.stdout)
	logger = logging.getLogger(__name__)
else:
	# Running under gunicorn so use their logger
	gunicorn_logger = logging.getLogger('gunicorn.error')
	logger = logging.getLogger(__name__)
	logger.setLevel(gunicorn_logger.level)
	logger.handlers = gunicorn_logger.handlers

# import the necessary packages
from flask import Response, Flask, render_template
import threading
import datetime
import imutils
import time
import cv2

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)

# initialize the video stream and allow the camera sensor to
# warmup
#vs = VideoStream(usePiCamera=1).start()
#vs = VideoStream(src=0).start()
vs = cv2.VideoCapture("/var/lib/vidstorage/testing.MOV")
time.sleep(2.0)

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

def detect_motion():
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame, lock
	
	ret, frame1 = vs.read()
	if not ret:
		return;

	frame1 = imutils.resize(frame1, width=720)

    # loop over frames from the video stream
	while True:
		ret, frame2 = vs.read()
		if not ret:
			break

		frame2 = imutils.resize(frame2, width=720)

		diff = cv2.absdiff(frame1, frame2)
		diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
		blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
		_, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
		dilated = cv2.dilate(thresh, None, iterations=3)

		contours, _ = cv2.findContours( dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
		for contour in contours:
			(x, y, w, h) = cv2.boundingRect(contour)
    		
			area = cv2.contourArea(contour)
			if area < 2000:
				continue

			#cv2.putText(frame1, "Size: {}".format(area), (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0 ,255), 2);
			cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)
			cv2.putText(frame1, "STATUS: {}".format('MOTION DETECTED'), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
			   1, (217, 10, 10), 2)
			


		# acquire the lock, set the output frame, and release the
		# lock
		with lock:
			outputFrame = frame1.copy()

		time.sleep(0.1)
		frame1 = frame2

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
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
			
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

# start a thread that will perform motion detection
t = threading.Thread(target=detect_motion, args=(), daemon=True)
t.start()

# Used for starting locally. Under gunircorn this won't get hit
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)