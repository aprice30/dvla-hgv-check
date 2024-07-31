from flask import Blueprint, render_template, request

# Define the blueprint
reports_bp = Blueprint('reports', __name__, template_folder='templates')

@reports_bp.route('/')
def browse():
    return render_template("browse.html", current_route=request.path)