"""backend/routes/pages.py"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/about")
def about():
    return render_template("pages/about.html")


@pages_bp.route("/privacy")
def privacy():
    return render_template("pages/privacy.html")


@pages_bp.route("/contact")
def contact():
    return render_template("pages/contact.html")
