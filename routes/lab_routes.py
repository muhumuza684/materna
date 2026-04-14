"""
routes/lab_routes.py
Lab Results Blueprint.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from routes.auth_routes import login_required
from extensions import db
from models.patient import Patient
from models.labs import LabResult

lab_bp = Blueprint("labs", __name__)


@lab_bp.route("/patients/<int:patient_id>/labs")
@login_required
def list_labs(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    labs = (LabResult.query
            .filter_by(patient_id=patient_id)
            .order_by(LabResult.result_date.desc())
            .all())
    return render_template("labs/list.html", patient=patient, labs=labs)


@lab_bp.route("/patients/<int:patient_id>/labs/create", methods=["GET", "POST"])
@login_required
def create_lab(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        try:
            test_name       = request.form.get("test_name", "").strip()
            value           = request.form.get("value", "").strip()
            interpretation  = request.form.get("interpretation", "").strip()
            result_date_str = request.form.get("result_date", "").strip()

            if not test_name or not value:
                flash("Test name and value are required.", "warning")
                return render_template("labs/create.html", patient=patient,
                                       today=datetime.utcnow().date().isoformat())

            result_date = (datetime.strptime(result_date_str, "%Y-%m-%d").date()
                           if result_date_str else datetime.utcnow().date())

            lab = LabResult(
                patient_id     = patient_id,
                test_name      = test_name,
                value          = value,
                interpretation = interpretation or None,
                result_date    = result_date,
            )
            db.session.add(lab)
            db.session.commit()
            flash("Lab result saved successfully.", "success")
            return redirect(url_for("patients.patient_detail", patient_id=patient_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving lab result: {str(e)}", "danger")

    today = datetime.utcnow().date().isoformat()
    return render_template("labs/create.html", patient=patient, today=today)
