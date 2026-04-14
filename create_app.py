"""
create_app.py
Application factory for the Maternal Health Management System.
"""

import os
from datetime import timedelta
from flask import Flask
from config import config_map
from extensions import db
from routes import BLUEPRINTS


def create_app(env: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ── Config ────────────────────────────────────────────────────────────────
    env = env or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config_map[env])

    # ✅ IMPORTANT: Allow DATABASE_URL from Render
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    # Session security
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=8))
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    # ── Instance folder ───────────────────────────────────────────────────────
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    # ── Database bootstrap (SAFE VERSION) ─────────────────────────────────────
    if app.config.get("AUTO_CREATE_DB", True):
        with app.app_context():
            import models  # registers models
            db.create_all()

    return app