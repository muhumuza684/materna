"""
services/rule_engine.py
Maternal Health Rule Engine — pure Python, no external dependencies.
"""


class RuleEngine:
    """
    Evaluates maternal health patient data against clinical rules and
    returns structured risk findings.
    """

    # ------------------------------------------------------------------ #
    #  Recommendation catalogue                                            #
    # ------------------------------------------------------------------ #
    _RECOMMENDATIONS = {
        "Hypertension Risk / Possible Pre-eclampsia": (
            "Monitor blood pressure every 15–30 minutes. "
            "Assess for pre-eclampsia symptoms (headache, visual changes, oedema). "
            "Consult obstetric team immediately."
        ),
        "Tachycardia": (
            "Investigate underlying cause (dehydration, infection, haemorrhage, anxiety). "
            "Perform 12-lead ECG if persistent. Ensure adequate hydration."
        ),
        "Bradycardia": (
            "Assess for haemodynamic instability. "
            "Review current medications for bradycardic side-effects. "
            "Continuous cardiac monitoring recommended."
        ),
        "Low Oxygen Saturation": (
            "Administer supplemental oxygen and reassess within 5 minutes. "
            "Evaluate for pulmonary embolism, pneumonia, or asthma exacerbation. "
            "Position patient in left lateral decubitus."
        ),
        "Fever": (
            "Obtain blood, urine, and vaginal cultures. "
            "Initiate antipyretic therapy and assess for chorioamnionitis or sepsis. "
            "Hydrate aggressively and monitor foetal heart rate."
        ),
        "Hypothermia": (
            "Apply warming measures (blankets, warm IV fluids). "
            "Investigate sepsis as a potential cause. "
            "Monitor core temperature continuously."
        ),
        "Obesity Risk": (
            "Refer to dietitian for gestational weight-gain counselling. "
            "Screen for gestational diabetes (GTT). "
            "Increase frequency of blood pressure monitoring."
        ),
        "Underweight Risk": (
            "Refer to dietitian for nutritional support plan. "
            "Assess for hyperemesis gravidarum or malabsorption. "
            "Monitor foetal growth with serial ultrasounds."
        ),
        "Anemia Risk": (
            "Confirm with full blood count and iron studies. "
            "Initiate oral iron supplementation. "
            "Consider IV iron if oral supplementation is not tolerated."
        ),
        "HIGH_RISK_ESCALATION": (
            "URGENT: Combination of elevated blood pressure and advanced gestational age "
            "significantly raises pre-eclampsia / eclampsia risk. "
            "Notify senior obstetrician immediately and prepare for possible delivery planning."
        ),
    }

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def analyze(self, patient_data: dict) -> dict:
        """
        Evaluate patient_data against maternal health rules.

        Expected keys (all optional — missing keys are silently skipped):
            systolic        (int/float)  — mmHg
            diastolic       (int/float)  — mmHg
            heart_rate      (int/float)  — bpm
            oxygen_sat      (int/float)  — %
            temperature     (int/float)  — °C
            bmi             (int/float)
            gestational_age (int/float)  — weeks
            hemoglobin      (int/float)  — g/dL

        Returns:
            {
                "risk_level":       "LOW" | "MEDIUM" | "HIGH",
                "flags":            [...],
                "recommendations":  [...],
                "summary":          "..."
            }
        """
        flags: list[str] = []
        recommendations: list[str] = []
        high_bp = False  # used for gestational-age escalation

        # ---- Blood Pressure ------------------------------------------ #
        systolic = self._get(patient_data, "systolic")
        diastolic = self._get(patient_data, "diastolic")
        if systolic is not None or diastolic is not None:
            if (systolic is not None and systolic > 140) or \
               (diastolic is not None and diastolic > 90):
                self._add_flag(
                    flags, recommendations,
                    "Hypertension Risk / Possible Pre-eclampsia"
                )
                high_bp = True

        # ---- Heart Rate ---------------------------------------------- #
        heart_rate = self._get(patient_data, "heart_rate")
        if heart_rate is not None:
            if heart_rate > 100:
                self._add_flag(flags, recommendations, "Tachycardia")
            elif heart_rate < 60:
                self._add_flag(flags, recommendations, "Bradycardia")

        # ---- Oxygen Saturation --------------------------------------- #
        oxygen_sat = self._get(patient_data, "oxygen_sat")
        if oxygen_sat is not None and oxygen_sat < 95:
            self._add_flag(flags, recommendations, "Low Oxygen Saturation")

        # ---- Temperature --------------------------------------------- #
        temperature = self._get(patient_data, "temperature")
        if temperature is not None:
            if temperature > 37.5:
                self._add_flag(flags, recommendations, "Fever")
            elif temperature < 36.0:
                self._add_flag(flags, recommendations, "Hypothermia")

        # ---- BMI ----------------------------------------------------- #
        bmi = self._get(patient_data, "bmi")
        if bmi is not None:
            if bmi > 30:
                self._add_flag(flags, recommendations, "Obesity Risk")
            elif bmi < 18.5:
                self._add_flag(flags, recommendations, "Underweight Risk")

        # ---- Hemoglobin (lab result) --------------------------------- #
        hemoglobin = self._get(patient_data, "hemoglobin")
        if hemoglobin is not None and hemoglobin < 11:
            self._add_flag(flags, recommendations, "Anemia Risk")

        # ---- Gestational Age + High BP escalation ------------------- #
        gestational_age = self._get(patient_data, "gestational_age")
        escalated = False
        if high_bp and gestational_age is not None and gestational_age >= 20:
            escalated = True
            # Add escalation recommendation if not already present
            escalation_rec = self._RECOMMENDATIONS["HIGH_RISK_ESCALATION"]
            if escalation_rec not in recommendations:
                recommendations.insert(0, escalation_rec)

        # ---- Risk Level --------------------------------------------- #
        risk_level = self._calculate_risk(flags, escalated)

        # ---- Summary ------------------------------------------------- #
        summary = self._build_summary(risk_level, flags)

        return {
            "risk_level": risk_level,
            "flags": flags,
            "recommendations": recommendations,
            "summary": summary,
        }

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get(data: dict, key: str):
        """Return a numeric value or None; silently skip non-numeric entries."""
        value = data.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _add_flag(
        self,
        flags: list[str],
        recommendations: list[str],
        flag: str,
    ) -> None:
        """Append a flag and its corresponding recommendation (once each)."""
        if flag not in flags:
            flags.append(flag)
        rec = self._RECOMMENDATIONS.get(flag)
        if rec and rec not in recommendations:
            recommendations.append(rec)

    @staticmethod
    def _calculate_risk(flags: list[str], escalated: bool) -> str:
        """
        Risk ladder:
          HIGH   — escalated (high BP + gestational age ≥ 20 wks)
                   OR 3+ flags
                   OR any immediately dangerous flag present
          MEDIUM — 1–2 flags
          LOW    — no flags
        """
        high_priority = {
            "Hypertension Risk / Possible Pre-eclampsia",
            "Low Oxygen Saturation",
            "Fever",
            "Hypothermia",
        }

        if escalated:
            return "HIGH"
        if not flags:
            return "LOW"
        if len(flags) >= 3:
            return "HIGH"
        if any(f in high_priority for f in flags):
            return "HIGH" if len(flags) >= 2 else "MEDIUM"
        return "MEDIUM"

    @staticmethod
    def _build_summary(risk_level: str, flags: list[str]) -> str:
        if not flags:
            return (
                "No clinical concerns detected; all assessed parameters "
                "are within normal maternal ranges."
            )
        flag_text = ", ".join(flags)
        level_phrase = {
            "LOW": "low-risk findings",
            "MEDIUM": "moderate clinical concerns",
            "HIGH": "high-risk findings requiring urgent attention",
        }.get(risk_level, "clinical findings")
        return (
            f"Patient presents with {level_phrase}: {flag_text}. "
            "Please review the recommendations and escalate as appropriate."
        )