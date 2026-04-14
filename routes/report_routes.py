"""
routes/report_routes.py
Patient Health Report Blueprint.
"""

from datetime import date
from flask import Blueprint, render_template, abort
from routes.auth_routes import login_required
from models.patient import Patient
from models.pregnancy import Pregnancy
from models.vitals import VitalSigns
from models.labs import LabResult
from models.appointments import Appointment

report_bp = Blueprint("reports", __name__)


def _calc_gestational_age(lmp_date):
    if not lmp_date:
        return ""
    delta = date.today() - lmp_date
    weeks, days = divmod(delta.days, 7)
    return f"{weeks}w {days}d"


def _trimester_label(lmp_date):
    if not lmp_date:
        return ""
    weeks = (date.today() - lmp_date).days // 7
    if weeks <= 12:   return "1st Trimester"
    elif weeks <= 27: return "2nd Trimester"
    else:             return "3rd Trimester"


def _risk_badge_colour(risk_level):
    return {"Low": "success", "Medium": "warning", "High": "danger"}.get(str(risk_level), "secondary")


def _appt_status_colour(status):
    return {"Pending": "warning", "Completed": "success", "Cancelled": "danger"}.get(status or "", "secondary")


@report_bp.route("/patients/<int:patient_id>/report")
@login_required
def patient_report(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        abort(404)

    pregnancies = (Pregnancy.query
                   .filter_by(patient_id=patient_id)
                   .order_by(Pregnancy.last_menstrual_period.desc())
                   .all())

    pregnancy_data = [{
        "obj":             pg,
        "gestational_age": _calc_gestational_age(pg.last_menstrual_period),
        "trimester":       _trimester_label(pg.last_menstrual_period),
        "risk_colour":     _risk_badge_colour(getattr(pg, "risk_level", "")),
    } for pg in pregnancies]

    vitals = (VitalSigns.query
              .filter_by(patient_id=patient_id)
              .order_by(VitalSigns.recorded_at.desc())
              .all())

    labs = (LabResult.query
            .filter_by(patient_id=patient_id)
            .order_by(LabResult.result_date.desc())
            .all())

    appointments = (Appointment.query
                    .filter_by(patient_id=patient_id)
                    .order_by(Appointment.appointment_date.desc())
                    .all())

    summary = {
        "pregnancies":     len(pregnancies),
        "vitals":          len(vitals),
        "labs":            len(labs),
        "appointments":    len(appointments),
        "pending_appts":   sum(1 for a in appointments if a.status == "Pending"),
        "completed_appts": sum(1 for a in appointments if a.status == "Completed"),
        "generated_on":    date.today().strftime("%d %B %Y"),
    }

    return render_template(
        "reports/patient_report.html",
        patient=patient,
        pregnancy_data=pregnancy_data,
        vitals=vitals,
        labs=labs,
        appointments=appointments,
        summary=summary,
        appt_status_colour=_appt_status_colour,
        risk_badge_colour=_risk_badge_colour,
    )
