"""
seed_admin.py
─────────────
Run ONCE after first launch to create the admin account.

    python seed_admin.py

Then log in at http://127.0.0.1:5000/auth/login
"""

from create_app import create_app
from extensions import db
from models.user import User, Role

app = create_app()

with app.app_context():
    if User.query.count() > 0:
        print("✗ Users already exist. Use /auth/register (as admin) to add more.")
    else:
        admin = User(username="admin", role=Role.ADMIN, is_active=True)
        admin.set_password("admin1234")
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created.")
        print("  Username : admin")
        print("  Password : admin1234")
        print("  → Change the password after first login!")
