"""
AI Health Assistance — Triage Engine
=====================================
Deterministic, explainable rules that map vitals and symptoms to a
three-level triage verdict (Low / Moderate / Critical risk).

Design principles:
- Explainable: every verdict lists *why* (which vitals flagged, which rules fired).
- Transparent: plain clinical reference bands, visible in one table below.
- Safe: always pairs a verdict with concrete next-step guidance.

NOTE: Educational demo only — NOT a medical device and NOT a diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Level(Enum):
    """Status of a single vital, or the overall triage verdict."""

    HEALTHY = "Healthy"
    CAUTION = "Caution"
    URGENT = "Urgent"


# --------------------------------------------------------------------------
# Vital reference bands
# (critical_low, caution_low, caution_high, critical_high, unit, label)
# Between caution_low..caution_high = Healthy; just outside = Caution;
# beyond critical bounds = Urgent.
# --------------------------------------------------------------------------
VITAL_RANGES: dict[str, tuple[float, float, float, float, str, str]] = {
    "heart_rate": (40, 50, 100, 135, "bpm", "Heart Rate"),
    "spo2": (88, 92, 100.5, 100.5, "%", "Oxygen Saturation (SpO2)"),
    "systolic": (80, 90, 130, 180, "mmHg", "Blood Pressure (Systolic)"),
    "diastolic": (50, 60, 85, 120, "mmHg", "Blood Pressure (Diastolic)"),
    "temperature": (94.0, 97.0, 99.5, 104.0, "°F", "Body Temperature"),
    "sleep": (0, 6.0, 10.0, 12.0, "hrs", "Sleep (last night)"),
}

# Composite scoring: every flagged vital adds flat risk points — simple
# enough to explain to a judge in one sentence, and it compounds sensibly:
#   1 caution ≈ 20  → Low          3 cautions ≈ 60 → Moderate
#   2 cautions ≈ 40 → Moderate     6 cautions cap at 55 (watch-list, not ER)
#   any urgent vital floors the score at 70 → Critical (never undersell red flags)
CAUTION_POINTS = 20
CAUTION_AGGREGATE_CAP = 55
URGENT_BASE = 65          # 1 urgent vital
URGENT_EXTRA = 35         # each additional urgent vital pushes toward 100
ANY_URGENT_FLOOR = 70

# Composite score bands → triage verdict.
SCORE_BANDS = ((0, 34, "Low"), (35, 64, "Moderate"), (65, 100, "Critical"))


def assess_vital(value: float, key: str) -> tuple[Level, str]:
    """Return (status, plain-English reason) for one vital reading."""
    crit_lo, warn_lo, warn_hi, crit_hi, unit, label = VITAL_RANGES[key]
    if value < crit_lo or value > crit_hi:
        direction = "very low" if value < crit_lo else "very high"
        return Level.URGENT, f"{label} {value:g} {unit} is critically {direction}"
    if value < warn_lo or value > warn_hi:
        direction = "low" if value < warn_lo else "elevated"
        return Level.CAUTION, f"{label} {value:g} {unit} is {direction} of the normal range"
    return Level.HEALTHY, f"{label} {value:g} {unit} is within the normal range"


@dataclass
class TriageResult:
    """Composite verdict with a full, human-readable explanation."""

    score: int  # 0 (all healthy) .. 100 (multi-vital emergency pattern)
    level: str  # "Low" | "Moderate" | "Critical"
    flags: list[tuple[str, Level, str]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def composite_triage(vitals: dict[str, float]) -> TriageResult:
    """Combine flagged vitals into one 0-100 score and a triage verdict."""
    flags: list[tuple[str, Level, str]] = []
    caution_points = 0
    n_urgent = 0

    for key in VITAL_RANGES:
        value = float(vitals.get(key, 0) or 0)
        level, reason = assess_vital(value, key)
        flags.append((key, level, reason))
        if level is Level.CAUTION:
            caution_points += CAUTION_POINTS
        elif level is Level.URGENT:
            n_urgent += 1

    score = min(caution_points, CAUTION_AGGREGATE_CAP)
    if n_urgent:
        urgent_score = min(100, URGENT_BASE + URGENT_EXTRA * (n_urgent - 1))
        score = max(score, urgent_score, ANY_URGENT_FLOOR)

    level = next(name for lo, hi, name in SCORE_BANDS if lo <= score <= hi)

    return TriageResult(
        score=score,
        level=level,
        flags=flags,
        recommendations=recommend_for(level, flags),
    )


def recommend_for(level: str, flags: list[tuple[str, Level, str]]) -> list[str]:
    """Concrete next steps — the 'what do I do now' part of triage."""
    urgent = [k for k, lvl, _ in flags if lvl is Level.URGENT]
    cautious = [k for k, lvl, _ in flags if lvl is Level.CAUTION]

    if level == "Critical":
        steps = [
            "🚨 Seek emergency care now — call your local emergency number.",
            "Do not drive yourself; have someone assist you.",
            "Share this dashboard snapshot with the responding clinicians.",
        ]
        if "spo2" in urgent:
            steps.insert(1, "Sit upright, loosen tight clothing, use prescribed oxygen if available.")
        if "systolic" in urgent or "diastolic" in urgent:
            steps.insert(1, "If experiencing chest pain, vision changes, or weakness — call emergency services immediately.")
        return steps
    if level == "Moderate":
        steps = [
            "📅 Book a doctor visit within 24–48 hours.",
            "Re-measure the flagged vitals after 15 minutes of rest.",
            f"Monitor closely: {' ,'.join(sorted(set(cautious + urgent))).replace('_', ' ')}.",
        ]
        if "temperature" in cautious or "temperature" in urgent:
            steps.append("💧 Hydrate and rest; use fever-reducing medication per label guidance.")
        if "sleep" in cautious:
            steps.append("😴 Prioritise a consistent sleep window tonight; avoid screens late.")
        return steps
    return [
        "✅ All core vitals look stable — keep up healthy routines.",
        "📈 Log readings daily to catch trends early.",
        "🧘 Light activity, hydration, and 7–9 hours of sleep maintain this status.",
    ]


# --------------------------------------------------------------------------
# Rule-based symptom chatbot (offline, deterministic)
# --------------------------------------------------------------------------
@dataclass
class SymptomRule:
    keywords: tuple[str, ...]
    level: str
    reply: str


SYMPTOM_RULES: tuple[SymptomRule, ...] = (
    SymptomRule(
        ("chest pain", "chest pressure", "chest tightness", "crushing chest"),
        "Critical",
        "Chest pain can signal a cardiac emergency, especially with sweating, arm/jaw pain, or shortness of breath. 🚨 Call emergency services now — do not wait and do not drive yourself.",
    ),
    SymptomRule(
        ("can't breathe", "cant breathe", "shortness of breath", "breathless", "hard to breathe", "gasping"),
        "Critical",
        "Difficulty breathing with low oxygen is an emergency. 🚨 Seek immediate care; sit upright, and use a rescue inhaler if prescribed.",
    ),
    SymptomRule(
        ("unconscious", "fainted", "passed out", "seizure", "stroke", "slurred speech", "face droop", "numb one side"),
        "Critical",
        "These are possible stroke/seizure red flags. 🚨 Call emergency services immediately — note the time symptoms started (clot-busting treatment is time-critical).",
    ),
    SymptomRule(
        ("vomiting blood", "blood in stool", "coughing blood", "black stool"),
        "Critical",
        "Blood loss symptoms need urgent evaluation. 🚨 Go to the emergency department now.",
    ),
    SymptomRule(
        ("severe bleeding", "bleeding heavily", "deep cut"),
        "Critical",
        "Apply firm pressure with a clean cloth, keep the area raised, and 🚨 call emergency services.",
    ),
    SymptomRule(
        ("fever", "temperature", "hot"),
        "Moderate",
        "Fever up to 3 days with fluids and rest is usually manageable at home. 📅 See a doctor within 24–48 hours if it exceeds 103°F, or is accompanied by stiff neck, rash, or confusion.",
    ),
    SymptomRule(
        ("headache", "migraine", "head hurts"),
        "Moderate",
        "Most headaches are manageable with hydration, rest, and OTC relief per label. 📅 Escalate if it is 'the worst ever', sudden-onset, or with fever/stiff neck — that needs same-day care.",
    ),
    SymptomRule(
        ("cough", "cold", "sore throat", "runny nose", "congestion", "flu"),
        "Low",
        "Viral symptoms typically resolve in 7–10 days. ✅ Rest, fluids, and humidified air help. Escalate if breathing becomes difficult or fever lasts beyond 3 days.",
    ),
    SymptomRule(
        ("tired", "fatigue", "exhausted", "weak", "dizzy", "lightheaded"),
        "Moderate",
        "Persistent fatigue can relate to sleep, anemia, thyroid, or hydration. 📅 Schedule a check-up with basic blood work within a few days — your Report Translator can decode the results.",
    ),
    SymptomRule(
        ("stomach", "abdominal", "nausea", "vomit", "diarrhea", "loose motion"),
        "Moderate",
        "Hydrate with ORS/electrolytes and eat light. 📅 See a doctor if pain localises to the lower right abdomen, lasts >48h, or you cannot keep fluids down.",
    ),
    SymptomRule(
        ("rash", "itching", "hives", "skin"),
        "Low",
        "Most rashes are mild irritations or allergies. ✅ Antihistamines and moisturisers often help. Escalate for rash + fever, blistering, or facial swelling (allergy emergency).",
    ),
    SymptomRule(
        ("anxiety", "panic", "stress", "depressed", "sad"),
        "Moderate",
        "Mental health is health. 📅 Book a clinician or counselor visit this week. If you have thoughts of self-harm, contact a crisis helpline immediately — you deserve support.",
    ),
    SymptomRule(
        ("back pain", "neck pain", "sprain", "muscle"),
        "Low",
        "Musculoskeletal pain usually improves with gentle movement, heat/ice, and OTC relief per label. ✅ Escalate for numbness, weakness, or bladder changes — those need prompt care.",
    ),
)


@dataclass
class ChatVerdict:
    level: str
    reply: str
    matched: str | None = None


def triage_symptoms(message: str) -> ChatVerdict:
    """Match free text against red-flag rules; fall back to a safe default."""
    text = message.lower()
    for rule in SYMPTOM_RULES:
        for kw in rule.keywords:
            if kw in text:
                return ChatVerdict(rule.level, rule.reply, matched=kw)

    # Duration heuristics push vague complaints toward the right channel.
    if any(w in text for w in ("week", "weeks", "month", "months")):
        return ChatVerdict(
            "Moderate",
            "Symptoms lasting weeks deserve a proper look. 📅 Book a clinician visit this week and bring any lab reports — I can translate those into plain English.",
        )
    return ChatVerdict(
        "Low",
        "Thanks for describing that. Based on what you've shared, this sounds manageable with rest and self-care. ✅ "
        "Tell me more — how long has it lasted, and does anything make it worse? I'll escalate if needed.",
    )
