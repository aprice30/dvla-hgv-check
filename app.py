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

# Register blueprints
from Reports.views import reports_bp
from Plate.views import plate_bp
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(plate_bp, url_prefix='/plate')


if __name__ == "__main__":
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
from datetime import datetime
from PlateProcessor.plate_processor import PlateProcessor
from PlateProcessor.plate_query import PlateQuery
from PlateProcessor.storage import Storage

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
plate_query = PlateQuery()

upload_to = "/home/myuser/data/grabs"

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.strftime(format)

app.jinja_env.filters['datetime'] = format_datetime

@app.before_request
def initialize():
    # Ensure our DB is setup before we try and use it
    if not hasattr(app, 'db_initialized'):
        storage = Storage()
        storage.init_db()
        app.db_initialized = True

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

		# Get the JSON data as we need it to know upload location		
		form = request.form
		json_str = form['json']
		json_data = json.loads(json_str)

		# Ensure our dir exists
		folder_path = os.path.dirname(json_data['data']['filename'])
		filename = os.path.basename(json_data['data']['filename'])
		upload_dir = os.path.join(upload_to, folder_path)
		if not os.path.exists(upload_dir):
			try:
				os.makedirs(upload_dir)
			except OSError as exc:  # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise

		for key in files.keys():  # The file doesn't exist under upload
			app.logger.debug(f"key: {key}")
			f = files[key]

			# Read the file content into bytes before saving
			file_content = f.read()
			file_path = os.path.join(upload_dir, filename)
			with open(file_path, 'wb') as file:
				file.write(file_content)

			# wait until the lock is acquired
			with lock:
				output_image = file_content
			break
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
	queue.enqueue(plate_processor.process, json_str)

	return resp

@app.route("/")
def home():
	# return the rendered template
	return render_template("home.html", current_route=request.path)

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

@app.route('/last_10_plates')
def last_10_plates():
	data = plate_query.get_latest_plates(10)
	return render_template('last_10_plates.html', rows=data)

@app.route('/plate_counts')
def plate_counts():
	data = plate_query.get_direction_plate_count()
	return render_template('plate_counts.html', rows=data)

@app.route('/weight_counts')
def weight_counts():
	data = plate_query.get_plates_by_weight()
	return render_template('plate_counts.html', rows=data)

# Used for starting locally. Under gunircorn this won't get hit
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)