"""
ai_service.py
Core wrapper for local LLM via Ollama.
Handles prompt construction, API calls, and response formatting.
"""

import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"  # Change to "llama3:8b", "mistral", etc. as needed
REQUEST_TIMEOUT = 60  # seconds

SYSTEM_PROMPT = """You are a maternal health assistant AI embedded in a clinical management system.

Your role:
- Summarize patient data clearly for healthcare providers
- Flag potential risk factors based on clinical values
- Use plain, professional language
- Structure your output with clear sections

Your strict limitations:
- You do NOT diagnose any condition
- You do NOT prescribe or recommend medications
- You do NOT replace clinical judgment
- You ALWAYS recommend consultation with a qualified healthcare provider
- When in doubt, flag for review rather than reassure

Every response must end with:
"⚠️ This is an AI-generated summary for informational purposes only. Always defer to a qualified healthcare provider for clinical decisions."
"""


def _call_ollama(prompt: str, system: Optional[str] = None) -> str:
    """
    Send a prompt to Ollama and return the response text.
    Raises RuntimeError on connection or API failure.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system or SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.3,     # Low temp = more consistent, safer outputs
            "top_p": 0.9,
            "num_predict": 800,
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        logger.error("Ollama not reachable at %s", OLLAMA_BASE_URL)
        raise RuntimeError(
            "AI service unavailable. Ensure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out after %ss", REQUEST_TIMEOUT)
        raise RuntimeError("AI service timed out. Try again shortly.")
    except requests.exceptions.HTTPError as e:
        logger.error("Ollama HTTP error: %s", e)
        raise RuntimeError(f"AI service error: {e}")


def is_ollama_available() -> bool:
    """Health check: returns True if Ollama is reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────────
# PUBLIC PROMPT BUILDERS
# ─────────────────────────────────────────────

def build_risk_prompt(patient_context: dict, rule_flags: list[dict]) -> str:
    """
    Build a structured risk analysis prompt.
    patient_context: dict from rag_service
    rule_flags: list of triggered rules from rule_engine
    """
    flags_text = ""
    if rule_flags:
        flags_text = "\n".join(
            f"  - [{f['severity'].upper()}] {f['message']}" for f in rule_flags
        )
    else:
        flags_text = "  - No critical rule violations detected."

    prompt = f"""
PATIENT RISK ANALYSIS REQUEST
==============================

PATIENT PROFILE:
{_format_patient_context(patient_context)}

AUTOMATED RULE ENGINE FLAGS:
{flags_text}

TASK:
Based on the data above, provide a structured risk assessment using this exact format:

RISK LEVEL: [Low / Medium / High]

KEY CONCERNS:
(List the top 2–4 clinical data points that drive the risk level)

EXPLANATION:
(2–4 sentences explaining what the data suggests in plain language. Do not diagnose.)

RECOMMENDED ACTIONS:
(What the care team should consider reviewing or following up on)
"""
    return prompt.strip()


def build_summary_prompt(patient_context: dict) -> str:
    """Build a patient summary prompt."""
    prompt = f"""
PATIENT SUMMARY REQUEST
========================

PATIENT PROFILE:
{_format_patient_context(patient_context)}

TASK:
Write a concise clinical summary (3–5 sentences) of this patient's current health status
based on the data provided. Cover: pregnancy status, recent vitals, lab findings, and
any patterns worth noting. Use plain professional language.

Format:
SUMMARY:
(Your summary here)

NOTABLE DATA POINTS:
(Bullet list of 2–4 specific values that stand out)
"""
    return prompt.strip()


def build_lab_interpretation_prompt(lab_data: dict) -> str:
    """Build a lab result interpretation prompt."""
    lab_lines = "\n".join(
        f"  {k}: {v}" for k, v in lab_data.items()
    )

    prompt = f"""
LAB RESULT INTERPRETATION REQUEST
===================================

LAB VALUES:
{lab_lines}

TASK:
Explain each lab result in simple language suitable for a patient or non-specialist.
For each value:
- State whether it is within a typical reference range
- Briefly explain what the test measures
- Note if it may warrant follow-up (without diagnosing)

Format your response as a clear list.
"""
    return prompt.strip()


# ─────────────────────────────────────────────
# PUBLIC AI FEATURE FUNCTIONS
# ─────────────────────────────────────────────

def analyze_risk(patient_context: dict, rule_flags: list[dict]) -> dict:
    """Run risk analysis. Returns structured dict."""
    prompt = build_risk_prompt(patient_context, rule_flags)
    raw = _call_ollama(prompt)
    return {
        "feature": "risk_analysis",
        "patient_id": patient_context.get("patient_id"),
        "rule_flags": rule_flags,
        "ai_response": raw,
        "model": OLLAMA_MODEL,
    }


def generate_summary(patient_context: dict) -> dict:
    """Generate patient summary. Returns structured dict."""
    prompt = build_summary_prompt(patient_context)
    raw = _call_ollama(prompt)
    return {
        "feature": "patient_summary",
        "patient_id": patient_context.get("patient_id"),
        "ai_response": raw,
        "model": OLLAMA_MODEL,
    }


def interpret_labs(lab_data: dict) -> dict:
    """Interpret lab results. Returns structured dict."""
    prompt = build_lab_interpretation_prompt(lab_data)
    raw = _call_ollama(prompt)
    return {
        "feature": "lab_interpretation",
        "input_labs": lab_data,
        "ai_response": raw,
        "model": OLLAMA_MODEL,
    }


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _format_patient_context(ctx: dict) -> str:
    """Pretty-print patient context dict for prompt insertion."""
    lines = []

    if ctx.get("patient"):
        p = ctx["patient"]
        lines.append(f"  Name: {p.get('name', 'N/A')}")
        lines.append(f"  Age: {p.get('age', 'N/A')}")
        lines.append(f"  Blood Type: {p.get('blood_type', 'N/A')}")

    if ctx.get("pregnancy"):
        pg = ctx["pregnancy"]
        lines.append(f"  Gestational Age: {pg.get('gestational_age_weeks', 'N/A')} weeks")
        lines.append(f"  Gravida/Para: G{pg.get('gravida', '?')} P{pg.get('para', '?')}")
        lines.append(f"  EDD: {pg.get('edd', 'N/A')}")
        lines.append(f"  High Risk: {pg.get('high_risk', False)}")

    if ctx.get("latest_vitals"):
        v = ctx["latest_vitals"]
        lines.append(f"  BP: {v.get('systolic', '?')}/{v.get('diastolic', '?')} mmHg")
        lines.append(f"  Heart Rate: {v.get('heart_rate', 'N/A')} bpm")
        lines.append(f"  Weight: {v.get('weight_kg', 'N/A')} kg")
        lines.append(f"  Temperature: {v.get('temperature_c', 'N/A')} °C")

    if ctx.get("recent_labs"):
        lines.append("  Recent Labs:")
        for lab in ctx["recent_labs"][:5]:
            lines.append(
                f"    • {lab.get('test_name')}: {lab.get('result')} {lab.get('unit', '')} "
                f"(ref: {lab.get('reference_range', 'N/A')})"
            )

    return "\n".join(lines) if lines else "  No data available."
