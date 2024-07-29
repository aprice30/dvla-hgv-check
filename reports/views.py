from flask import Blueprint, render_template

# Define the blueprint
reports_bp = Blueprint('reports', __name__, template_folder='templates')

@reports_bp.route('/')
def index():
    return render_template("browse.html")