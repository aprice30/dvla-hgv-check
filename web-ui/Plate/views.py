from flask import Blueprint, render_template, request, send_from_directory
import Plate.queries

# Define the blueprint
plate_bp = Blueprint('plate', __name__, template_folder='templates')

@plate_bp.route('/images/<path:filename>')
def images(filename):
    upload_to = "/home/myuser/data/grabs"
    return send_from_directory(upload_to, filename)

@plate_bp.route('/<plate_str>')
def plate(plate_str: str):

    # Fetch plate history
    rows = Plate.queries.get_plate_results(plate_str)

    return render_template("index.html", current_route=request.path, rows=rows, plate=plate_str)

