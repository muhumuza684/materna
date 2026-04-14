"""
routes/vitals_routes.py
Vital signs Blueprint — with Rule Engine integration.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from routes.auth_routes import login_required
from extensions import db
from models.patient import Patient
from models.vitals import VitalSigns
from services.rule_engine import RuleEngine

vitals_bp = Blueprint("vitals", __name__)
_rule_engine = RuleEngine()


# ─────────────────────────────────────────────
# HELPER: parse "120/80" → (120, 80) or (None, None)
# ─────────────────────────────────────────────
def _parse_bp(bp_string: str):
    """
    Split a 'systolic/diastolic' string into two floats.
    Returns (None, None) if the string is missing or malformed.
    """
    if not bp_string:
        return None, None
    try:
        parts = bp_string.strip().split("/")
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except (ValueError, AttributeError):
        pass
    return None, None


# ─────────────────────────────────────────────
# HELPER: build patient_data dict for RuleEngine
# ─────────────────────────────────────────────
def _build_rule_input(vital: VitalSigns, patient_id: int) -> dict:
    """
    Assemble a flat dict from a VitalSigns record that the
    RuleEngine.analyze() method understands.
    Hemoglobin is pulled from the most recent lab result if available.
    """
    systolic, diastolic = _parse_bp(vital.blood_pressure)

    data = {
        "systolic":    systolic,
        "diastolic":   diastolic,
        "heart_rate":  vital.heart_rate,
        "temperature": vital.temperature,
        "bmi":         vital.bmi,
        "oxygen_sat":  vital.oxygen_saturation,
    }

    # Pull gestational age from the most recent pregnancy record
    try:
        from models.pregnancy import Pregnancy
        preg = (
            Pregnancy.query
            .filter_by(patient_id=patient_id)
            .order_by(Pregnancy.id.desc())
            .first()
        )
        if preg:
            if hasattr(preg, "lmp") and preg.lmp:
                weeks = (datetime.today().date() - preg.lmp).days // 7
                data["gestational_age"] = weeks
            elif hasattr(preg, "gestational_age_weeks") and preg.gestational_age_weeks:
                data["gestational_age"] = preg.gestational_age_weeks
    except Exception:
        pass  # Pregnancy model unavailable — skip silently

    # Pull latest hemoglobin from lab results
    try:
        from models.labs import LabResult
        hb_lab = (
            LabResult.query
            .filter(
                LabResult.patient_id == patient_id,
                LabResult.test_name.ilike("%hemoglobin%"),
            )
            .order_by(LabResult.collected_at.desc())
            .first()
        )
        if hb_lab and hb_lab.result:
            data["hemoglobin"] = float(hb_lab.result)
    except Exception:
        pass  # Lab model unavailable — skip silently

    return data


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@vitals_bp.route("/patients/<int:patient_id>/vitals")
@login_required
def list_vitals(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    vitals = (
        VitalSigns.query
        .filter_by(patient_id=patient_id)
        .order_by(VitalSigns.recorded_at.desc())
        .all()
    )
    return render_template("vitals/list.html", patient=patient, vitals=vitals)


@vitals_bp.route("/patients/<int:patient_id>/vitals/create", methods=["GET", "POST"])
@login_required
def create_vitals(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        try:
            blood_pressure    = request.form.get("blood_pressure", "").strip()
            heart_rate        = request.form.get("heart_rate")
            temperature       = request.form.get("temperature")
            weight            = request.form.get("weight")
            bmi               = request.form.get("bmi")
            oxygen_saturation = request.form.get("oxygen_saturation")

            vital = VitalSigns(
                patient_id        = patient_id,
                blood_pressure    = blood_pressure or None,
                heart_rate        = float(heart_rate)        if heart_rate        else None,
                temperature       = float(temperature)       if temperature       else None,
                weight            = float(weight)            if weight            else None,
                bmi               = float(bmi)               if bmi               else None,
                oxygen_saturation = float(oxygen_saturation) if oxygen_saturation else None,
                recorded_at       = datetime.utcnow(),
            )
            db.session.add(vital)
            db.session.commit()

            # ── Rule Engine Analysis ──────────────────────────────────
            rule_input  = _build_rule_input(vital, patient_id)
            analysis    = _rule_engine.analyze(rule_input)
            risk_level  = analysis.get("risk_level", "LOW")
            flags       = analysis.get("flags", [])

            # Surface findings to the nurse via flash messages
            if risk_level == "HIGH":
                flash(
                    f"⚠ HIGH RISK — {', '.join(flags) if flags else 'Multiple concerns detected'}. "
                    "Review recommendations immediately.",
                    "danger"
                )
            elif risk_level == "MEDIUM":
                flash(
                    f"⚠ Moderate concern — {', '.join(flags)}. Please review.",
                    "warning"
                )
            else:
                flash("Vital signs recorded successfully. No critical flags detected.", "success")

            # Pass full analysis to detail page so it can be rendered
            return redirect(
                url_for(
                    "vitals.vitals_analysis",
                    patient_id=patient_id,
                    vital_id=vital.id,
                )
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving vitals: {str(e)}", "danger")

    return render_template("vitals/create.html", patient=patient)


@vitals_bp.route("/patients/<int:patient_id>/vitals/<int:vital_id>/analysis")
@login_required
def vitals_analysis(patient_id, vital_id):
    """
    Show the rule engine analysis for a specific vitals record.
    This is the page the nurse lands on after saving vitals.
    """
    patient = Patient.query.get_or_404(patient_id)
    vital   = VitalSigns.query.get_or_404(vital_id)

    rule_input = _build_rule_input(vital, patient_id)
    analysis   = _rule_engine.analyze(rule_input)

    return render_template(
        "vitals/analysis.html",
        patient=patient,
        vital=vital,
        analysis=analysis,
    )