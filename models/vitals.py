"""
models/vitals.py
----------------
A point-in-time snapshot of a patient's vital signs.
Multiple readings can be recorded per visit.
"""

from datetime import datetime, timezone
from extensions import db


class VitalSigns(db.Model):
    __tablename__ = "vital_signs"

    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    # Blood pressure stored as a string to preserve "120/80" format exactly.
    blood_pressure    = db.Column(db.String(20), nullable=True)   # e.g. "120/80"
    heart_rate        = db.Column(db.Integer,    nullable=True)   # bpm
    temperature       = db.Column(db.Float,      nullable=True)   # °C
    weight            = db.Column(db.Float,      nullable=True)   # kg
    bmi               = db.Column(db.Float,      nullable=True)   # kg/m²
    oxygen_saturation = db.Column(db.Float,      nullable=True)   # % SpO₂

    recorded_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<VitalSigns id={self.id} patient_id={self.patient_id} "
            f"bp='{self.blood_pressure}' recorded_at='{self.recorded_at}'>"
        )
