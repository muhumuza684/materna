"""
models/appointments.py
Scheduled clinical appointments linked to a patient.
"""

from datetime import datetime
from extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    appointment_date = db.Column(db.Date,    nullable=False)
    appointment_time = db.Column(db.Time,    nullable=True)
    type             = db.Column(db.String(100), nullable=True)
    provider_name    = db.Column(db.String(120), nullable=True)
    status           = db.Column(db.String(20),  nullable=False, default="Pending")
    notes            = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status_badge(self):
        return {"Pending": "warning", "Completed": "success", "Cancelled": "danger"}.get(self.status, "secondary")

    def __repr__(self):
        return f"<Appointment id={self.id} patient_id={self.patient_id} status='{self.status}'>"
