"""
models/pregnancy.py
-------------------
Tracks a single pregnancy episode for a patient.
A patient may have multiple pregnancy records over time.
"""

import enum
from datetime import datetime, timezone
from extensions import db


class RiskLevel(str, enum.Enum):
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"


class PregnancyStatus(str, enum.Enum):
    ACTIVE    = "Active"
    COMPLETED = "Completed"


class Pregnancy(db.Model):
    __tablename__ = "pregnancies"

    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    # Core obstetric dates
    last_menstrual_period = db.Column(db.Date, nullable=False)
    estimated_due_date    = db.Column(db.Date, nullable=True)

    # Calculated / clinician-entered fields
    gestational_age_weeks = db.Column(db.Integer, nullable=True)   # whole weeks
    trimester             = db.Column(db.Integer, nullable=True)   # 1 | 2 | 3

    risk_level = db.Column(
        db.Enum(RiskLevel),
        nullable=False,
        default=RiskLevel.LOW,
    )
    status = db.Column(
        db.Enum(PregnancyStatus),
        nullable=False,
        default=PregnancyStatus.ACTIVE,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Pregnancy id={self.id} patient_id={self.patient_id} "
            f"status='{self.status.value}' risk='{self.risk_level.value}'>"
        )
