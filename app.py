#-----------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#-----------------------------------------------------------------------------------------

# Setup logging first
import logging.handlers
import logging, sys
from flask import Response, Flask, render_template, request, jsonify # type: ignore
	
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
import json
import os
import errno

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
globalOutput = None
globalJson = None
lock = threading.Lock()

@app.route('/send', methods = ['GET'])
def get_index():
	return "Please use GET request type", 400

upload_to = "/home/myuser/data/grabs"

@app.route('/send', methods = ['POST'])
def post_index():
	# grab global references
	global globalOutput, globalJson, lock

	resp = Response("OK", 200)
	resp.headers['Content-type'] = 'text/html'

	# Files exist for multipart/form-data
	files = request.files
	if files:
		app.logger.debug(f"files: {files}")
		app.logger.debug("Request contains image")
		if not os.path.exists(upload_to):
			try:
				os.makedirs(upload_to)
			except OSError as exc:  # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise

		for key in files.keys():  # The file doesn't exist under upload
			app.logger.debug(f"key: {key}")
			f = files[key]

			# Read the file content into bytes before saving
			file_content = f.read()
			file_path = os.path.join(upload_to, f.filename)
			with open(file_path, 'wb') as file:
				file.write(file_content)

			# wait until the lock is acquired
			with lock:
				globalOutput = file_content
			break

		form = request.form
		jsonData = json.loads(form["json"])
	else:
		app.logger.debug("Request contains json")
		try:
			jsonStr = request.form.get('json')
			jsonData = json.loads(jsonStr)
		except json.JSONDecodeError as e:
			logging.exception("Unable to decode json from payload")
			jsonData = {}

	# wait until the lock is acquired
	with lock:
		globalJson = jsonData

	app.logger.info(f"json_data: {jsonData}")
	return resp

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

@app.route("/data")
def data():
	# grab global references
	global globalJson, lock

    # wait until the lock is acquired
	with lock:
		return jsonify(globalJson)

def generate_capture():
	# grab global references
	global globalOutput, lock
	
	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop
			if globalOutput is None:
				continue
			
			# yield the output frame in the byte format
			yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
				bytearray(globalOutput) + b'\r\n')

@app.route("/capture")
def capture():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate_capture(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

# Used for starting locally. Under gunircorn this won't get hit
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)