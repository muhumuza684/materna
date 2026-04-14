"""
routes/patient_routes.py
------------------------
Blueprint: patient_bp
Prefix   : /patients

Routes
------
GET  /patients              — list all patients
GET  /patients/create       — show create form
POST /patients/create       — handle create form submission
GET  /patients/<int:id>     — show single patient detail
"""

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth_routes import login_required

from extensions import db
from models.patient import Patient

patient_bp = Blueprint("patients", __name__, url_prefix="/patients")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_patient_form(form) -> dict:
    """Extract and lightly sanitise form fields into a plain dict."""
    raw_dob = form.get("date_of_birth", "").strip()
    try:
        dob = datetime.strptime(raw_dob, "%Y-%m-%d").date()
    except ValueError:
        dob = None

    return {
        "full_name":         form.get("full_name",         "").strip(),
        "date_of_birth":     dob,
        "contact_info":      form.get("contact_info",      "").strip() or None,
        "blood_type":        form.get("blood_type",        "").strip() or None,
        "medical_history":   form.get("medical_history",   "").strip() or None,
        "allergies":         form.get("allergies",         "").strip() or None,
        "medications":       form.get("medications",       "").strip() or None,
        "emergency_contact": form.get("emergency_contact", "").strip() or None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@patient_bp.route("/")
@login_required
def list_patients():
    """Display all patients, newest first."""
    patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template("patients/list.html", patients=patients)


@patient_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_patient():
    """Show and handle the create-patient form."""
    if request.method == "POST":
        data = _parse_patient_form(request.form)

        # Basic validation
        if not data["full_name"]:
            flash("Full name is required.", "danger")
            return render_template("patients/create.html", form=request.form)

        if data["date_of_birth"] is None:
            flash("A valid date of birth is required (YYYY-MM-DD).", "danger")
            return render_template("patients/create.html", form=request.form)

        patient = Patient(**data)
        db.session.add(patient)
        db.session.commit()

        flash(f"Patient '{patient.full_name}' added successfully.", "success")
        return redirect(url_for("patients.list_patients"))

    # GET — empty form
    return render_template("patients/create.html", form={})


@patient_bp.route("/<int:patient_id>")
@login_required
def patient_detail(patient_id: int):
    """Show full details for a single patient."""
    patient = Patient.query.get_or_404(patient_id)
    return render_template("patients/detail.html", patient=patient)
