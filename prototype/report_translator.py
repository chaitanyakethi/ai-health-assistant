"""
AI Health Assistance — Medical Report Translator
=================================================
Turns a complex lab report (PDF or pasted text) into a plain-English
summary. In production this stage is an LLM call; the prototype ships a
deterministic regex-based extractor so the demo is reproducible offline.

Pipeline: extract text → find lab analytes + values → look up reference
intervals → explain each line in plain English → visual summary.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Reference intervals — (low, high, unit, plain-English "why it matters")
# Sources: standard clinical reference ranges (educational use).
# ---------------------------------------------------------------------------
REFERENCE: dict[str, dict] = {
    "Hemoglobin": {
        "range": (13.0, 17.0), "unit": "g/dL",
        "why": "carries oxygen through your blood — low levels cause tiredness and weakness",
        "aliases": ("hemoglobin", "haemoglobin", "hb", "hgb"),
    },
    "WBC": {
        "range": (4000, 11000), "unit": "cells/µL",
        "why": "your infection-fighting cells — high suggests infection/inflammation, low weakens immunity",
        "aliases": ("wbc", "total leukocyte", "tlc", "leucocyte count", "leukocyte count"),
    },
    "Platelets": {
        "range": (150000, 410000), "unit": "/µL",
        "why": "help blood clot — low raises bleeding risk, very high raises clot risk",
        "aliases": ("platelets", "platelet count", "plt"),
    },
    "Glucose": {
        "range": (70, 99), "unit": "mg/dL (fasting)",
        "why": "your body's fuel — persistently high points toward diabetes risk",
        "aliases": ("glucose fasting", "fasting glucose", "fasting blood sugar", "fbs", "blood sugar", "glucose"),
    },
    "HbA1c": {
        "range": (4.0, 5.6), "unit": "%",
        "why": "average blood sugar over ~3 months — the key diabetes control marker",
        "aliases": ("hba1c", "a1c", "glycated haemoglobin", "glycosylated haemoglobin"),
    },
    "Cholesterol": {
        "range": (0, 200), "unit": "mg/dL",
        "why": "a fat in your blood — high levels build up in artery walls over years",
        "aliases": ("total cholesterol", "cholesterol total", "cholesterol", "chole"),
    },
    "Triglycerides": {
        "range": (0, 150), "unit": "mg/dL",
        "why": "blood fats that rise with sugar/fried food and alcohol",
        "aliases": ("triglycerides", "trigly", "tg"),
    },
    "TSH": {
        "range": (0.4, 4.0), "unit": "µIU/mL",
        "why": "your thyroid's control signal — off-balance affects energy, weight, and mood",
        "aliases": ("thyroid stimulating hormone", "thyrotropin", "tsh"),
    },
    "Vitamin D": {
        "range": (30, 100), "unit": "ng/mL",
        "why": "supports bones and immunity — deficiency is very common and easily fixed",
        "aliases": ("vitamin d", "vit d", "25-oh vitamin d", "25-hydroxyvitamin d"),
    },
    "Vitamin B12": {
        "range": (200, 900), "unit": "pg/mL",
        "why": "keeps nerves and blood cells healthy — low causes tingling and fatigue",
        "aliases": ("vitamin b12", "b12", "cobalamin"),
    },
    "Creatinine": {
        "range": (0.6, 1.3), "unit": "mg/dL",
        "why": "a kidney-filter check — rising values mean the kidneys need attention",
        "aliases": ("creatinine", "serum creatinine", "creat"),
    },
    "Urea": {
        "range": (15, 40), "unit": "mg/dL",
        "why": "another kidney filter marker — read together with creatinine",
        "aliases": ("blood urea", "urea", "bun"),
    },
}

# Order matters: longest aliases first so "fasting glucose" wins over "glucose".
_ALIAS_ORDER = sorted(
    ((alias, name) for name, cfg in REFERENCE.items() for alias in cfg["aliases"]),
    key=lambda pair: -len(pair[0]),
)


@dataclass
class LabLine:
    """One extracted lab value plus its plain-English interpretation."""

    analyte: str
    value: float
    unit: str
    status: str  # "Normal" | "High" | "Low"
    why: str
    range_text: str


def _extract_text(uploaded) -> str:
    """Read an uploaded Streamlit file, raw bytes, or a plain string into text."""
    if isinstance(uploaded, str):
        return uploaded
    raw = uploaded.getvalue() if hasattr(uploaded, "getvalue") else bytes(uploaded)
    if (getattr(uploaded, "name", "") or "").lower().endswith(".pdf") or raw[:4] == b"%PDF":
        try:
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # noqa: BLE001 — surface a friendly demo error
            return f"[Could not read PDF: {exc}]"
    return raw.decode("utf-8", errors="replace")


def _find_analyte(line: str) -> tuple[str | None, int]:
    """Return (analyte name, index just after the matched alias) on the line."""
    low = line.lower()
    for alias, name in _ALIAS_ORDER:
        pos = low.find(alias)
        if pos != -1:
            return name, pos + len(alias)
    return None, 0


def _find_value(line: str) -> float | None:
    """Grab the first plausible numeric result on the line."""
    import re

    # Prefer a plain number that is NOT part of a reference range like "13-17"
    candidates = []
    for match in re.finditer(r"\d+(?:\.\d+)?", line):
        value = float(match.group())
        before, after = line[: match.start()], line[match.end() :]
        # skip values inside hyphen/–/to ranges, or followed by % with letters
        if after.lstrip().startswith(("-", "–", "to")):
            continue
        if before.rstrip().endswith(("-", "–")):
            continue
        candidates.append(value)
    return candidates[0] if candidates else None


def translate_report(source) -> dict:
    """Convert report text/PDF into a structured, explained summary dict."""
    text = _extract_text(source)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    results: list[LabLine] = []
    seen: set[str] = set()

    for line in lines:
        name, after = _find_analyte(line)
        if not name or name in seen:
            continue
        # Scan for the value AFTER the analyte name so digits inside names
        # (HbA1c, B12) are never mistaken for the result.
        value = _find_value(line[after:])
        if value is None:
            continue
        seen.add(name)
        cfg = REFERENCE[name]
        lo, hi = cfg["range"]
        status = "Normal"
        if value < lo:
            status = "Low"
        elif value > hi:
            status = "High"
        results.append(
            LabLine(
                analyte=name,
                value=value,
                unit=cfg["unit"],
                status=status,
                why=cfg["why"],
                range_text=f"{lo:g}–{hi:g} {cfg['unit']}",
            )
        )

    abnormal = [r for r in results if r.status != "Normal"]
    headline = (
        f"{len(abnormal)} of {len(results)} markers outside reference range"
        if results
        else "No recognised lab markers found in this document"
    )
    return {"results": results, "abnormal": abnormal, "headline": headline, "raw": text}
