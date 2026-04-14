"""
models/labs.py
--------------
Stores individual laboratory test results linked to a patient.
One row = one test on one date.
"""

from datetime import date
from extensions import db


class LabResult(db.Model):
    __tablename__ = "lab_results"

    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    test_name      = db.Column(db.String(120), nullable=False)   # e.g. "Hemoglobin"
    value          = db.Column(db.String(100), nullable=True)    # e.g. "11.2 g/dL"
    interpretation = db.Column(db.Text,        nullable=True)    # clinician notes

    result_date = db.Column(
        db.Date,
        nullable=False,
        default=date.today,
    )

    def __repr__(self) -> str:
        return (
            f"<LabResult id={self.id} patient_id={self.patient_id} "
            f"test='{self.test_name}' date='{self.result_date}'>"
        )
