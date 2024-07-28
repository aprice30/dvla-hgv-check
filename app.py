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
import threading, json, os, errno
import redis, requests
from rq import Queue
from PlateProcessor.plate_processor import PlateProcessor
from Model import model

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

# Create a plate processor which will handle all processing of the plate results
plate_processor = PlateProcessor()

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
			app.logger.exception("Unable to decode json from payload")
			json_data = {}

	# wait until the lock is acquired
	with lock:
		output_json = json_data

	# Hand over now to our processor to do further work on this result
	app.logger.info(f"json_data: {json_data}")
	root = model.Root(**json_data)
	queue.enqueue(plate_processor.process, root)


	# data = json_data.get('data')
	# if data is not None:
	# 	queue.enqueue(plate_processor.process, data)
	# else:
	# 	app.logger.warning(f"Unable to process JSON as expecting 'data' sub element")

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