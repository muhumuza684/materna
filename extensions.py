"""
extensions.py
-------------
Flask extensions are instantiated here WITHOUT being tied to any specific
Flask app.  The app factory in create_app() calls init_app() on each
extension to bind them at runtime.  This pattern avoids circular imports.
"""

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy instance — imported by models and the app factory
db = SQLAlchemy()
