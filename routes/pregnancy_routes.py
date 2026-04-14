"""
routes/pregnancy_routes.py
--------------------------
Blueprint : pregnancy_bp
URL prefix: /patients/<patient_id>/pregnancies

Routes
------
GET  /patients/<id>/pregnancies           — list all pregnancies for a patient
GET  /patients/<id>/pregnancies/create    — show create form
POST /patients/<id>/pregnancies/create    — handle form submission
"""

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth_routes import login_required

from extensions import db
from models.patient import Patient
from models.pregnancy import Pregnancy, RiskLevel, PregnancyStatus

pregnancy_bp = Blueprint("pregnancies", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(raw: str):
    """Return a date object or None from a YYYY-MM-DD string."""
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _parse_int(raw: str):
    """Return an int or None from a string."""
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@pregnancy_bp.route("/patients/<int:patient_id>/pregnancies")
@login_required
def list_pregnancies(patient_id: int):
    """List all pregnancy records for a given patient."""
    patient     = Patient.query.get_or_404(patient_id)
    pregnancies = (
        Pregnancy.query
        .filter_by(patient_id=patient_id)
        .order_by(Pregnancy.created_at.desc())
        .all()
    )
    return render_template(
        "pregnancy/list.html",
        patient=patient,
        pregnancies=pregnancies,
    )


@pregnancy_bp.route(
    "/patients/<int:patient_id>/pregnancies/create",
    methods=["GET", "POST"],
)
@login_required
def create_pregnancy(patient_id: int):
    """Show and process the create-pregnancy form."""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        form = request.form

        lmp = _parse_date(form.get("last_menstrual_period", ""))
        edd = _parse_date(form.get("estimated_due_date", ""))
        ga  = _parse_int(form.get("gestational_age_weeks", ""))
        tri = _parse_int(form.get("trimester", ""))

        # --- Validation --------------------------------------------------
        errors = []

        if lmp is None:
            errors.append("Last Menstrual Period date is required.")

        raw_trimester = form.get("trimester", "").strip()
        if raw_trimester and tri not in (1, 2, 3):
            errors.append("Trimester must be 1, 2, or 3.")

        raw_risk   = form.get("risk_level", "").strip()
        raw_status = form.get("status", "").strip()

        try:
            risk_level = RiskLevel(raw_risk)
        except ValueError:
            errors.append("Invalid risk level.")
            risk_level = RiskLevel.LOW

        try:
            status = PregnancyStatus(raw_status)
        except ValueError:
            errors.append("Invalid status.")
            status = PregnancyStatus.ACTIVE

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "pregnancy/create.html",
                patient=patient,
                form=form,
            )

        # --- Persist -----------------------------------------------------
        pregnancy = Pregnancy(
            patient_id=patient_id,
            last_menstrual_period=lmp,
            estimated_due_date=edd,
            gestational_age_weeks=ga,
            trimester=tri,
            risk_level=risk_level,
            status=status,
        )
        db.session.add(pregnancy)
        db.session.commit()

        flash("Pregnancy record added successfully.", "success")
        return redirect(url_for("patients.patient_detail", patient_id=patient_id))

    # GET — empty form
    return render_template("pregnancy/create.html", patient=patient, form={})
