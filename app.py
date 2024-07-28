#-----------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#-----------------------------------------------------------------------------------------

# Setup logging first
import logging.handlers
import logging, sys
import DvlaClient.DvlaClient
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
import redis
import requests
from rq import Queue
from DvlaClient.DvlaClient import DvlaClient

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
output_image = None
output_json = None
lock = threading.Lock()

# Set up Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_conn = redis.Redis.from_url(redis_url)

# Initialize an RQ queue
queue = Queue(connection=redis_conn)

# Create a DVLA client so we can query plates
api_key = "?????"
dvla_client = DvlaClient(api_key)

upload_to = "/home/myuser/data/grabs"

@app.route('/plate_detected', methods = ['POST'])
def plate_detected():
	# grab global references
	global output_image, output_json, lock

	resp = Response("OK", 200)
	resp.headers['Content-type'] = 'text/html'

	# Files exist for multipart/form-data
	files = request.files
	if files:
		app.logger.debug("Request contains image")
		app.logger.debug(f"files: {files}")
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
				output_image = file_content
			break

		form = request.form
		json_data = json.loads(form["json"])
	else:
		app.logger.debug("Request contains json")
		try:
			json_str = request.form.get('json')
			json_data = json.loads(json_str)
		except json.JSONDecodeError as e:
			logging.exception("Unable to decode json from payload")
			json_data = {}

	# wait until the lock is acquired
	with lock:
		output_json = json_data

	# Send our plate data for further processing
	for result in json_data['data']['results']:
		for candidate in result['candidates']:
			logging.info(f"Running DVLA check against Plate={candidate['plate']}")
			queue.enqueue(dvla_client.check_plate, candidate['plate'])
	
	app.logger.info(f"json_data: {json_data}")
	return resp

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

@app.route("/data")
def data():
	# grab global references
	global output_json, lock

    # wait until the lock is acquired
	with lock:
		return jsonify(output_json)

def generate_capture():
	# grab global references
	global output_image, lock
	
	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop
			if output_image is None:
				continue
			
			# yield the output frame in the byte format
			yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
				bytearray(output_image) + b'\r\n')

@app.route("/capture")
def capture():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate_capture(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

# Used for starting locally. Under gunircorn this won't get hit
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)