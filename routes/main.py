"""
routes/main.py
--------------
Main Blueprint: handles the root URL and a /health endpoint.
This is the only "real" blueprint wired up at project initialisation.
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@main_bp.route("/health")
def health_check():
    """Simple liveness probe — useful for deployment checks."""
    return {"status": "ok", "service": "Maternal Health Management System"}, 200
