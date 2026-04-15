"""
routes/auth_routes.py
Improved Authentication Blueprint with proper multi-user support.
"""

from functools import wraps
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   request, session, flash, g)
from extensions import db
from models.user import User, Role

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not session.get("user_id"):
                flash("Please log in.", "warning")
                return redirect(url_for("auth.login"))
            if user is None or user.role not in roles:
                flash("You do not have permission.", "danger")
                return redirect(url_for("main.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


@auth_bp.before_app_request
def load_logged_in_user():
    g.current_user = get_current_user()


# ── Routes ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    existing_users = User.query.count()
    current = get_current_user()

    # FIRST USER → becomes Admin automatically
    if existing_users == 0:
        default_role = Role.ADMIN
    else:
        default_role = request.form.get("role", Role.NURSE)

    # Restrict registration to Admin after first user
    if existing_users > 0 and (current is None or not current.is_admin):
        flash("Only administrators can create new users.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm_password", "").strip()
        role     = default_role

        error = None
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif role not in Role.ALL:
            error = "Invalid role."
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' is already taken."

        if error:
            flash(error, "danger")
            return render_template("auth/register.html", roles=Role.ALL)

        user = User(username=username, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f"Account for '{username}' created successfully.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", roles=Role.ALL)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    no_users_yet = User.query.count() == 0

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", no_users_yet=no_users_yet)

        if not user.is_active:
            flash("Your account has been deactivated.", "warning")
            return render_template("auth/login.html", no_users_yet=no_users_yet)

        session.clear()
        session["user_id"] = user.id
        session["user_role"] = user.role

        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome back, {user.username}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.index"))

    return render_template("auth/login.html", no_users_yet=no_users_yet)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/users")
@roles_required(Role.ADMIN)
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("auth/user_list.html", users=users)


@auth_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@roles_required(Role.ADMIN)
def toggle_user(user_id):
    user = db.session.get(User, user_id)

    if user is None:
        flash("User not found.", "danger")

    elif user.id == session["user_id"]:
        flash("You cannot deactivate your own account.", "warning")

    else:
        user.is_active = not user.is_active
        db.session.commit()
        state = "activated" if user.is_active else "deactivated"
        flash(f"User '{user.username}' {state}.", "success")

    return redirect(url_for("auth.user_list"))