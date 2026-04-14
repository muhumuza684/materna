"""
models/user.py
User model with role-based access control.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class Role:
    ADMIN  = "Admin"
    DOCTOR = "Doctor"
    NURSE  = "Nurse"
    ALL    = ["Admin", "Doctor", "Nurse"]

    PERMISSIONS = {
        "Admin":  {"can_view_patients": True, "can_edit_patients": True,
                   "can_delete_patients": True, "can_add_vitals": True,
                   "can_add_labs": True, "can_add_appointments": True,
                   "can_view_reports": True, "can_manage_users": True},
        "Doctor": {"can_view_patients": True, "can_edit_patients": True,
                   "can_delete_patients": True, "can_add_vitals": True,
                   "can_add_labs": True, "can_add_appointments": True,
                   "can_view_reports": True, "can_manage_users": False},
        "Nurse":  {"can_view_patients": True, "can_edit_patients": False,
                   "can_delete_patients": False, "can_add_vitals": True,
                   "can_add_labs": True, "can_add_appointments": True,
                   "can_view_reports": False, "can_manage_users": False},
    }

    @classmethod
    def has_permission(cls, role, permission):
        return cls.PERMISSIONS.get(role, {}).get(permission, False)


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default=Role.NURSE)
    is_active     = db.Column(db.Boolean, default=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        return Role.has_permission(self.role, permission)

    @property
    def is_admin(self):  return self.role == Role.ADMIN
    @property
    def is_doctor(self): return self.role == Role.DOCTOR
    @property
    def is_nurse(self):  return self.role == Role.NURSE

    def __repr__(self):
        return f"<User {self.username!r} role={self.role!r}>"
