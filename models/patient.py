"""
models/patient.py
-----------------
Patient is the central entity of the system.
All other models reference Patient via a foreign key.
"""

from datetime import datetime, timezone
from extensions import db


class Patient(db.Model):
    __tablename__ = "patients"

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)

    # Contact details stored as a single free-text field for flexibility.
    # Can be refactored into discrete columns (phone, email, address) later.
    contact_info      = db.Column(db.String(255), nullable=True)
    blood_type        = db.Column(db.String(10), nullable=True)   # e.g. "A+", "O-"

    # Long-form clinical fields
    medical_history = db.Column(db.Text, nullable=True)
    allergies       = db.Column(db.Text, nullable=True)
    medications     = db.Column(db.Text, nullable=True)

    emergency_contact = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    pregnancies  = db.relationship("Pregnancy",   backref="patient", lazy="dynamic", cascade="all, delete-orphan")
    vitals       = db.relationship("VitalSigns",  backref="patient", lazy="dynamic", cascade="all, delete-orphan")
    lab_results  = db.relationship("LabResult",   backref="patient", lazy="dynamic", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="patient", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name='{self.full_name}'>"
