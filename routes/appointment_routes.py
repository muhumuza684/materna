"""
routes/appointment_routes.py
Appointments Blueprint.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from routes.auth_routes import login_required
from extensions import db
from models.patient import Patient
from models.appointments import Appointment

appointment_bp = Blueprint("appointments", __name__)

APPOINTMENT_TYPES    = ["Antenatal", "Checkup", "Emergency", "Postnatal", "Ultrasound"]
APPOINTMENT_STATUSES = ["Pending", "Completed", "Cancelled"]


def _get_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        abort(404)
    return patient


@appointment_bp.route("/patients/<int:patient_id>/appointments")
@login_required
def list_appointments(patient_id):
    patient = _get_patient(patient_id)
    appointments = (Appointment.query
                    .filter_by(patient_id=patient_id)
                    .order_by(Appointment.appointment_date.desc(),
                              Appointment.appointment_time.desc())
                    .all())
    return render_template("appointments/list.html",
                           patient=patient, appointments=appointments)


@appointment_bp.route("/patients/<int:patient_id>/appointments/create",
                      methods=["GET", "POST"])
@login_required
def create_appointment(patient_id):
    patient = _get_patient(patient_id)

    if request.method == "POST":
        errors = []
        raw_date  = request.form.get("appointment_date", "").strip()
        raw_time  = request.form.get("appointment_time", "").strip()
        appt_type = request.form.get("type", "").strip()
        provider  = request.form.get("provider_name", "").strip()
        notes     = request.form.get("notes", "").strip()

        if not raw_date:  errors.append("Appointment date is required.")
        if not raw_time:  errors.append("Appointment time is required.")
        if appt_type not in APPOINTMENT_TYPES: errors.append("Select a valid appointment type.")
        if not provider:  errors.append("Provider name is required.")

        appt_date = appt_time = None
        if raw_date:
            try:    appt_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except: errors.append("Invalid date format.")
        if raw_time:
            try:    appt_time = datetime.strptime(raw_time, "%H:%M").time()
            except: errors.append("Invalid time format.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("appointments/create.html",
                                   patient=patient,
                                   appointment_types=APPOINTMENT_TYPES,
                                   form_data=request.form)

        appt = Appointment(
            patient_id       = patient_id,
            appointment_date = appt_date,
            appointment_time = appt_time,
            type             = appt_type,
            provider_name    = provider,
            notes            = notes or None,
            status           = "Pending",
        )
        db.session.add(appt)
        db.session.commit()
        flash("Appointment scheduled successfully.", "success")
        return redirect(url_for("appointments.list_appointments", patient_id=patient_id))

    return render_template("appointments/create.html",
                           patient=patient,
                           appointment_types=APPOINTMENT_TYPES,
                           form_data={})


@appointment_bp.route("/appointments/<int:appointment_id>/update-status", methods=["POST"])
@login_required
def update_status(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in APPOINTMENT_STATUSES:
        flash("Invalid status value.", "danger")
        return redirect(url_for("appointments.list_appointments",
                                patient_id=appt.patient_id))

    appt.status = new_status
    db.session.commit()
    flash(f"Appointment marked as {new_status}.", "success")
    return redirect(url_for("appointments.list_appointments",
                            patient_id=appt.patient_id))
