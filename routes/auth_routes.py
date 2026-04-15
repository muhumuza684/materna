"""
routes/auth_routes.py
Improved authentication system (production-ready for Render)
"""

from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, session, flash, g
)

from extensions import db
from models.user import User, Role

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────
# Helpers
# ─────────────────────────────

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


@auth_bp.before_app_request
def load_logged_in_user():
    g.user = get_current_user()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()

            if not user:
                flash("Login required.", "warning")
                return redirect(url_for("auth.login"))

            if user.role not in roles:
                flash("Access denied.", "danger")
                return redirect(url_for("main.index"))

            return view(*args, **kwargs)
        return wrapped
    return decorator


# ─────────────────────────────
# REGISTER
# ─────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    users_exist = User.query.count() > 0
    current_user = get_current_user()

    # Only admin can create users after first setup
    if users_exist and (not current_user or not current_user.is_admin):
        flash("Only admin can create new accounts.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        role = request.form.get("role", Role.NURSE)

        # validation
        if not username:
            flash("Username required.", "danger")
        elif not password:
            flash("Password required.", "danger")
        elif len(password) < 6:
            flash("Password too short.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif role not in Role.ALL:
            flash("Invalid role.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
        else:
            user = User(username=username, role=role)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Account created successfully. Please login.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", roles=Role.ALL)


# ─────────────────────────────
# LOGIN (FIXED)
# ─────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Account disabled.", "warning")
            return render_template("auth/login.html")

        # clear old session and set new
        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role

        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome {user.username}", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.index"))

    return render_template("auth/login.html")


# ─────────────────────────────
# LOGOUT
# ─────────────────────────────

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))