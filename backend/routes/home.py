"""backend/routes/home.py"""
from flask import Blueprint, render_template
from flask_login import current_user

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    return render_template("home.html")
