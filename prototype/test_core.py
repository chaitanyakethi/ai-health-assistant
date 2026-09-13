"""Smoke tests for the triage engine and report translator."""

from report_translator import translate_report
from triage import Level, assess_vital, composite_triage, triage_symptoms

HEALTHY = {
    "heart_rate": 72, "spo2": 98, "systolic": 118,
    "diastolic": 76, "temperature": 98.6, "sleep": 7.5,
}


def test_healthy_baseline_is_low():
    result = composite_triage(HEALTHY)
    assert result.level == "Low" and result.score <= 34


def test_low_o2_alone_escalates_to_critical():
    vitals = dict(HEALTHY, spo2=85)
    result = composite_triage(vitals)
    assert result.level == "Critical"
    assert any(lvl is Level.URGENT for _, lvl, _ in result.flags)


def test_moderate_mix():
    vitals = dict(HEALTHY, heart_rate=105, sleep=5.0)
    result = composite_triage(vitals)
    assert result.level in ("Moderate", "Critical") and result.score >= 35


def test_vital_bands():
    assert assess_vital(72, "heart_rate")[0] is Level.HEALTHY
    assert assess_vital(105, "heart_rate")[0] is Level.CAUTION
    assert assess_vital(150, "heart_rate")[0] is Level.URGENT
    assert assess_vital(90, "spo2")[0] is Level.CAUTION
    assert assess_vital(85, "spo2")[0] is Level.URGENT


def test_symptom_red_flags():
    assert triage_symptoms("crushing chest pain").level == "Critical"
    assert triage_symptoms("I can't breathe properly").level == "Critical"
    assert triage_symptoms("slurred speech and face droop").level == "Critical"


def test_symptom_moderate_and_default():
    assert triage_symptoms("mild fever since yesterday").level == "Moderate"
    assert triage_symptoms("runny nose and cough").level == "Low"
    assert triage_symptoms("something vague").level == "Low"
    assert triage_symptoms("tired for weeks").level == "Moderate"


def test_report_translation_from_text():
    report = "Hemoglobin 10.2 g/dL\nFasting Glucose 128 mg/dL\nTSH 6.1 uIU/mL\nPlatelets 250000 /uL"
    result = translate_report(report)
    names = {r.analyte for r in result["results"]}
    assert {"Hemoglobin", "Glucose", "TSH", "Platelets"} <= names
    status = {r.analyte: r.status for r in result["results"]}
    assert status["Hemoglobin"] == "Low"
    assert status["Glucose"] == "High"
    assert status["TSH"] == "High"
    assert status["Platelets"] == "Normal"
    assert len(result["abnormal"]) == 3


def test_report_range_numbers_not_confused_with_values():
    # "13-17" style reference ranges must not be picked up as the value.
    report = "Hemoglobin 10.2 g/dL (ref 13-17)"
    result = translate_report(report)
    hb = result["results"][0]
    assert hb.value == 10.2 and hb.status == "Low"
