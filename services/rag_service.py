"""
rag_service.py
Retrieval-Augmented Generation context builder.

Assembles all relevant patient data into a single context dict
that feeds into both the rule engine and the AI prompt.

No vector DB needed at this scale — we query the existing
Flask/SQLAlchemy models directly and structure the output.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# MAIN CONTEXT BUILDER
# ─────────────────────────────────────────────

def build_patient_context(patient_id: int, db_models: dict) -> dict:
    """
    Assemble a complete patient context dict for AI processing.

    db_models: dict of SQLAlchemy model classes, e.g.:
    {
        "Patient": Patient,
        "Vitals": Vitals,
        "Lab": Lab,
        "Pregnancy": Pregnancy,
        "Appointment": Appointment,
    }

    Returns a flat, JSON-serialisable dict.
    """
    Patient = db_models.get("Patient")
    Vitals = db_models.get("Vitals")
    Lab = db_models.get("Lab")
    Pregnancy = db_models.get("Pregnancy")
    Appointment = db_models.get("Appointment")

    patient = _get_patient(Patient, patient_id)
    if not patient:
        raise ValueError(f"Patient {patient_id} not found.")

    context = {
        "patient_id": patient_id,
        "retrieved_at": datetime.utcnow().isoformat(),

        # Core patient info
        "patient": _serialize_patient(patient),

        # Pregnancy info (latest active)
        "pregnancy": _get_pregnancy(Pregnancy, patient_id),

        # Most recent vitals
        "latest_vitals": _get_latest_vitals(Vitals, patient_id),

        # Labs from last 90 days
        "recent_labs": _get_recent_labs(Lab, patient_id, days=90),

        # Upcoming / recent appointments
        "appointments": _get_appointments(Appointment, patient_id),

        # Embedded medical reference rules (static knowledge base)
        "reference_context": MEDICAL_REFERENCE,
    }

    return context


# ─────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────

def _get_patient(Patient, patient_id: int):
    if Patient is None:
        return None
    try:
        return Patient.query.get(patient_id)
    except Exception as e:
        logger.warning("Could not fetch patient %s: %s", patient_id, e)
        return None


def _serialize_patient(patient) -> dict:
    """Serialize patient model to safe dict."""
    if patient is None:
        return {}

    age = None
    if hasattr(patient, "date_of_birth") and patient.date_of_birth:
        today = datetime.today()
        dob = patient.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    return {
        "id": getattr(patient, "id", None),
        "name": getattr(patient, "name", None) or (
            f"{getattr(patient, 'first_name', '')} {getattr(patient, 'last_name', '')}".strip()
        ),
        "age": age,
        "blood_type": getattr(patient, "blood_type", None),
        "phone": getattr(patient, "phone", None),
        "allergies": getattr(patient, "allergies", None),
        "medical_history": getattr(patient, "medical_history", None),
    }


def _get_pregnancy(Pregnancy, patient_id: int) -> Optional[dict]:
    if Pregnancy is None:
        return None
    try:
        # Get the most recent pregnancy record
        preg = (
            Pregnancy.query
            .filter_by(patient_id=patient_id)
            .order_by(Pregnancy.id.desc())
            .first()
        )
        if not preg:
            return None

        gest_weeks = None
        if hasattr(preg, "lmp") and preg.lmp:
            gest_weeks = (datetime.today().date() - preg.lmp).days // 7
        elif hasattr(preg, "gestational_age_weeks"):
            gest_weeks = preg.gestational_age_weeks

        return {
            "gestational_age_weeks": gest_weeks,
            "gravida": getattr(preg, "gravida", None),
            "para": getattr(preg, "para", None),
            "edd": str(getattr(preg, "edd", None) or ""),
            "lmp": str(getattr(preg, "lmp", None) or ""),
            "high_risk": getattr(preg, "high_risk", False),
            "risk_factors": getattr(preg, "risk_factors", None),
            "blood_group": getattr(preg, "blood_group", None),
        }
    except Exception as e:
        logger.warning("Could not fetch pregnancy for %s: %s", patient_id, e)
        return None


def _get_latest_vitals(Vitals, patient_id: int) -> Optional[dict]:
    if Vitals is None:
        return None
    try:
        v = (
            Vitals.query
            .filter_by(patient_id=patient_id)
            .order_by(Vitals.recorded_at.desc())
            .first()
        )
        if not v:
            return None

        return {
            "recorded_at": str(getattr(v, "recorded_at", "")),
            "systolic": getattr(v, "systolic", None),
            "diastolic": getattr(v, "diastolic", None),
            "heart_rate": getattr(v, "heart_rate", None),
            "weight_kg": getattr(v, "weight_kg", None),
            "temperature_c": getattr(v, "temperature_c", None),
            "oxygen_saturation": getattr(v, "oxygen_saturation", None),
            "respiratory_rate": getattr(v, "respiratory_rate", None),
        }
    except Exception as e:
        logger.warning("Could not fetch vitals for %s: %s", patient_id, e)
        return None


def _get_recent_labs(Lab, patient_id: int, days: int = 90) -> list[dict]:
    if Lab is None:
        return []
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        labs = (
            Lab.query
            .filter(
                Lab.patient_id == patient_id,
                Lab.collected_at >= cutoff
            )
            .order_by(Lab.collected_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "test_name": getattr(l, "test_name", None),
                "result": getattr(l, "result", None),
                "unit": getattr(l, "unit", None),
                "reference_range": getattr(l, "reference_range", None),
                "abnormal_flag": getattr(l, "abnormal_flag", None),
                "collected_at": str(getattr(l, "collected_at", "")),
            }
            for l in labs
        ]
    except Exception as e:
        logger.warning("Could not fetch labs for %s: %s", patient_id, e)
        return []


def _get_appointments(Appointment, patient_id: int) -> dict:
    if Appointment is None:
        return {}
    try:
        now = datetime.utcnow()
        upcoming = (
            Appointment.query
            .filter(
                Appointment.patient_id == patient_id,
                Appointment.appointment_date >= now
            )
            .order_by(Appointment.appointment_date.asc())
            .first()
        )
        last = (
            Appointment.query
            .filter(
                Appointment.patient_id == patient_id,
                Appointment.appointment_date < now
            )
            .order_by(Appointment.appointment_date.desc())
            .first()
        )

        return {
            "next_appointment": str(getattr(upcoming, "appointment_date", "") or ""),
            "last_appointment": str(getattr(last, "appointment_date", "") or ""),
        }
    except Exception as e:
        logger.warning("Could not fetch appointments for %s: %s", patient_id, e)
        return {}


# ─────────────────────────────────────────────
# STATIC MEDICAL REFERENCE (Embedded Knowledge)
# ─────────────────────────────────────────────
# This is the "R" in RAG — injected into the AI prompt
# as a lightweight knowledge base so the model has
# maternal health reference ranges available.

MEDICAL_REFERENCE = {
    "description": "Maternal health reference ranges (WHO / RCOG guidelines)",
    "vitals": {
        "blood_pressure": {
            "normal": "< 120/80 mmHg",
            "elevated": "120–139/80–89 mmHg",
            "high": "≥ 140/90 mmHg",
            "severe": "≥ 160/110 mmHg",
        },
        "heart_rate": {"normal": "60–100 bpm"},
        "temperature": {"normal": "36.1–37.2 °C", "fever": "≥ 38.0 °C"},
        "oxygen_saturation": {"normal": "≥ 95%"},
    },
    "labs": {
        "hemoglobin_pregnancy": {
            "normal": "≥ 11.0 g/dL (1st & 3rd trimester)",
            "mild_anemia": "10.0–10.9 g/dL",
            "moderate_anemia": "7.0–9.9 g/dL",
            "severe_anemia": "< 7.0 g/dL",
        },
        "fasting_glucose": {
            "normal": "< 5.6 mmol/L",
            "impaired": "5.6–6.9 mmol/L",
            "diabetic": "≥ 7.0 mmol/L",
        },
        "proteinuria": {
            "normal": "< 150 mg/24hr",
            "significant": "≥ 300 mg/24hr (pre-eclampsia threshold)",
        },
        "platelets": {
            "normal": "150–400 × 10⁹/L",
            "low": "< 100 × 10⁹/L",
            "critical": "< 50 × 10⁹/L",
        },
    },
    "risk_conditions": [
        "Pre-eclampsia: BP ≥140/90 + proteinuria ≥300mg after 20 weeks",
        "Gestational Diabetes: fasting glucose ≥5.6 or 2hr OGTT ≥7.8",
        "Anaemia: Hb < 10.5 in pregnancy",
        "HELLP: Haemolysis + Elevated Liver enzymes + Low Platelets",
        "Preterm labour risk: contractions before 37 weeks",
    ],
}


# ─────────────────────────────────────────────
# UTILITY: build context from raw dicts (testing / API use)
# ─────────────────────────────────────────────

def build_context_from_raw(
    patient: dict,
    vitals: Optional[dict] = None,
    labs: Optional[list] = None,
    pregnancy: Optional[dict] = None,
) -> dict:
    """
    Build context from raw dicts (useful for lab interpretation endpoint
    where a full DB lookup isn't needed).
    """
    return {
        "patient_id": patient.get("id"),
        "retrieved_at": datetime.utcnow().isoformat(),
        "patient": patient,
        "latest_vitals": vitals or {},
        "recent_labs": labs or [],
        "pregnancy": pregnancy or {},
        "reference_context": MEDICAL_REFERENCE,
    }
