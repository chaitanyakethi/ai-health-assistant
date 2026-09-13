"""
AI Health Assistance — Live Dashboard Prototype
===============================================
Run:  streamlit run app.py

A real-time health dashboard that decodes medical jargon, triages
symptoms, and visualises vitals — built for live judge demos.

Stack: Streamlit + Plotly (all logic offline & deterministic).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from report_translator import translate_report
from triage import (
    Level,
    VITAL_RANGES,
    assess_vital,
    composite_triage,
    triage_symptoms,
)

# ---------------------------------------------------------------------------
# Page setup & design tokens
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Health Assistance",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUS_COLOR = {
    Level.HEALTHY: ("#16a34a", "🟢"),
    Level.CAUTION: ("#f59e0b", "🟡"),
    Level.URGENT: ("#dc2626", "🔴"),
}
LEVEL_COLOR = {"Low": "#16a34a", "Moderate": "#f59e0b", "Critical": "#dc2626"}
LEVEL_EMOJI = {"Low": "🟢", "Moderate": "🟡", "Critical": "🔴"}

st.markdown(
    """
    <style>
      .vital-card {border-radius: 14px; padding: 14px 16px; border: 1px solid rgba(128,128,128,.25);}
      .vital-value {font-size: 2rem; font-weight: 800; line-height: 1.1;}
      .vital-label {font-size: .82rem; opacity: .75; margin-bottom: 2px;}
      .reason {font-size: .78rem; margin-top: 6px;}
      .big-verdict {border-radius: 16px; padding: 18px 22px; color: white;}
      .chat-user {background: rgba(59,130,246,.15); border-radius: 12px; padding: 10px 14px; margin: 6px 0;}
      .chat-bot  {background: rgba(128,128,128,.12); border-radius: 12px; padding: 10px 14px; margin: 6px 0;}
      .tag {border-radius: 999px; padding: 2px 10px; font-size: .72rem; font-weight: 700; color: white;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
DEFAULT_VITALS = {
    "heart_rate": 72.0,
    "spo2": 98.0,
    "systolic": 118.0,
    "diastolic": 76.0,
    "temperature": 98.6,
    "sleep": 7.5,
}

if "vitals" not in st.session_state:
    st.session_state.vitals = dict(DEFAULT_VITALS)
if "chat" not in st.session_state:
    st.session_state.chat = [
        {
            "role": "bot",
            "text": "Hi! Describe how you're feeling — e.g. “I've had a headache and mild fever since yesterday.” I'll assess urgency and tell you the next best step.",
        }
    ]
if "report" not in st.session_state:
    st.session_state.report = None

# ---------------------------------------------------------------------------
# Sidebar — demo controls
# ---------------------------------------------------------------------------
def apply_scenario(**values: float) -> None:
    """Update vitals AND the slider widgets' own state.

    Without seeding the ``s_*`` widget keys, sliders would silently restore
    their previous values on the next rerun and clobber the scenario
    (button says Critical, sliders say healthy). Seeding keeps them in sync.
    """
    st.session_state.vitals.update(values)
    for key, value in values.items():
        st.session_state[f"s_{key}"] = float(value)


with st.sidebar:
    st.title("🩺 AI Health Assistance")
    st.caption("Decodes jargon • Triages symptoms • Visualises vitals")
    st.divider()
    st.subheader("Demo controls")
    if st.button("🎬 Scenario: Emergency (low O₂ + high BP)", width='stretch'):
        apply_scenario(
            heart_rate=122.0, spo2=87.0, systolic=185.0, diastolic=115.0, temperature=101.8, sleep=4.0
        )
        st.rerun()
    if st.button("⚠️ Scenario: Watch-list (slightly off)", width='stretch'):
        apply_scenario(
            heart_rate=104.0, spo2=93.0, systolic=138.0, diastolic=88.0, temperature=100.2, sleep=5.5
        )
        st.rerun()
    if st.button("✅ Scenario: Healthy baseline", width='stretch'):
        apply_scenario(**DEFAULT_VITALS)
        st.rerun()
    st.divider()
    st.caption(
        "**Educational prototype — not a medical device.** "
        "Logic is deterministic and explainable for judge transparency; "
        "production swaps the rules for a fine-tuned medical LLM (see architecture doc)."
    )

# ---------------------------------------------------------------------------
# Header + overall verdict
# ---------------------------------------------------------------------------
result = composite_triage(st.session_state.vitals)
verdict_color = LEVEL_COLOR[result.level]

st.markdown(
    f"""
    <div class="big-verdict" style="background: {verdict_color};">
      <div style="font-size:.85rem; opacity:.9; letter-spacing:2px;">LIVE TRIAGE VERDICT</div>
      <div style="font-size:2rem; font-weight:800;">{LEVEL_EMOJI[result.level]} {result.level} Risk — Composite Score {result.score}/100</div>
      <div style="font-size:.9rem; opacity:.95;">{result.recommendations[0]}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_vitals, tab_report, tab_chat = st.tabs(
    ["📡 Vitals Dashboard", "📄 Report Translator", "💬 Symptom Triage Chat"]
)

# === TAB 1 — VITALS =========================================================
with tab_vitals:
    left, right = st.columns([3, 2], gap="large")

    with left:
        # Controls FIRST so a slider move instantly re-renders the cards below
        # (the script reruns top-to-bottom with fresh session_state values).
        st.subheader("🎛️ Simulate wearable stream")
        slider_cols = st.columns(3)
        # All-float bounds/steps keep Streamlit's slider type rules happy.
        spans = {
            "heart_rate": (30.0, 190.0, "Heart Rate"),
            "spo2": (70.0, 100.0, "SpO₂"),
            "systolic": (70.0, 200.0, "Systolic BP"),
            "diastolic": (40.0, 130.0, "Diastolic BP"),
            "temperature": (93.0, 106.0, "Temperature"),
            "sleep": (0.0, 12.0, "Sleep"),
        }
        for i, (key, (lo, hi, name)) in enumerate(spans.items()):
            with slider_cols[i % 3]:
                step = 0.1 if key in ("temperature", "sleep", "spo2") else 1.0
                st.session_state.vitals[key] = st.slider(
                    name, lo, hi, float(st.session_state.vitals[key]), step=step, key=f"s_{key}"
                )

        st.subheader("Vitals Panel")
        keys = list(VITAL_RANGES.keys())
        for row_start in range(0, len(keys), 2):
            cols = st.columns(2)
            for col, key in zip(cols, keys[row_start : row_start + 2]):
                value = st.session_state.vitals[key]
                _, _, _, _, unit, label = VITAL_RANGES[key]
                level, reason = assess_vital(value, key)
                color, dot = STATUS_COLOR[level]
                with col:
                    st.markdown(
                        f"""
                        <div class="vital-card" style="border-top: 4px solid {color};">
                          <div class="vital-label">{dot} {label}</div>
                          <div class="vital-value" style="color:{color};">{value:g} <span style="font-size:.9rem;opacity:.6">{unit}</span></div>
                          <div class="reason">{reason}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write("")

    with right:
        st.subheader("Smart Triage Gauge")
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=result.score,
                number={"suffix": "/100"},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": verdict_color},
                    "steps": [
                        {"range": [0, 35], "color": "rgba(22,163,74,.25)"},
                        {"range": [35, 65], "color": "rgba(245,158,11,.25)"},
                        {"range": [65, 100], "color": "rgba(220,38,38,.30)"},
                    ],
                },
            )
        )
        fig.update_layout(height=260, margin=dict(t=30, b=10, l=25, r=25))
        st.plotly_chart(fig, width='stretch')

        st.subheader("Recommended Next Steps")
        for rec in result.recommendations:
            st.markdown(f"- {rec}")

        st.subheader("Why this verdict (explainability)")
        st.caption("Every flag maps to a visible clinical band — no black box.")
        for key, level, reason in result.flags:
            color, dot = STATUS_COLOR[level]
            st.markdown(f"- {dot} {reason}")

        st.subheader("24-hour trend (simulated)")
        trend_fig = go.Figure()
        hours = list(range(24))
        # Deterministic wobble so the demo chart never flickers between reruns.
        wobble = [0, 1.5, -1, 2, -2.5, 1, 0.5, -1.5, 2.5, -2, 0, 1,
                  -1, 2, 0.5, -2.5, 1.5, 0, -1, 1, 2, -1.5, 0.5, -0.5]
        for key, name, color in [
            ("heart_rate", "Heart Rate", "#ef4444"),
            ("spo2", "SpO₂", "#3b82f6"),
        ]:
            base = st.session_state.vitals[key]
            series = [round(base + w, 1) for w in wobble]
            trend_fig.add_trace(go.Scatter(x=hours, y=series, name=name, line={"color": color}))
        trend_fig.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10), yaxis_title=None)
        st.plotly_chart(trend_fig, width='stretch')

# === TAB 2 — REPORT TRANSLATOR ==============================================
with tab_report:
    st.subheader("Medical Report Translator")
    st.caption(
        "Upload a lab-report PDF (or paste text) → get a plain-English summary. "
        "The demo extractor is deterministic; production routes the same output shape through a fine-tuned medical LLM."
    )

    up_left, up_right = st.columns(2)
    with up_left:
        uploaded = st.file_uploader("📤 Lab report (PDF/TXT)", type=["pdf", "txt"])
        if uploaded is not None and st.button("Decode report", type="primary", width='stretch'):
            st.session_state.report = translate_report(uploaded)
    with up_right:
        sample = st.text_area(
            "…or paste report text",
            height=140,
            placeholder="Hemoglobin 10.2 g/dL\nFasting Glucose 128 mg/dL\nTSH 6.1 µIU/mL",
        )
        if st.button("Decode pasted text", width='stretch') and sample.strip():
            st.session_state.report = translate_report(sample)

    if st.session_state.report:
        rep = st.session_state.report
        st.info(f"**Summary:** {rep['headline']}")
        st.markdown("###### 🧾 Complex input → 💬 Plain English (split view)")
        for r in rep["results"]:
            color = {"Normal": "#16a34a", "High": "#dc2626", "Low": "#f59e0b"}[r.status]
            st.markdown(
                f"""
                <div class="vital-card" style="display:flex; justify-content:space-between; align-items:center; margin:8px 0;">
                  <div>
                    <b>{r.analyte}: {r.value:g} {r.unit}</b>
                    <div class="reason">💬 {r.why}</div>
                  </div>
                  <div style="text-align:right;">
                    <span class="tag" style="background:{color};">{r.status}</span>
                    <div class="reason">ref {r.range_text}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if rep["abnormal"]:
            st.warning(
                "📅 Bring this summary to your doctor within a few days. "
                + " ".join(f"**{r.analyte}** is {r.status.lower()}." for r in rep["abnormal"])
            )
    else:
        st.caption("👆 Decode a report to see the split view here.")

# === TAB 3 — SYMPTOM CHAT ===================================================
with tab_chat:
    st.subheader("Smart Symptom Triage Chat")
    st.caption("Red-flag rules fire first (safety), then guidance — deterministic and auditable.")

    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 <b>You:</b> {msg["text"]}</div>', unsafe_allow_html=True)
        else:
            tag_color = LEVEL_COLOR[msg.get("level", "Low")]
            tag = (
                f'<span class="tag" style="background:{tag_color};">{msg["level"]} risk</span> '
                if msg.get("level")
                else ""
            )
            st.markdown(
                f'<div class="chat-bot">🩺 <b>Assistant:</b> {tag}<br>{msg["text"]}</div>',
                unsafe_allow_html=True,
            )

    quick_cols = st.columns(4)
    quick_prompts = [
        "Crushing chest pain",
        "Mild fever since yesterday",
        "Tired and dizzy for a week",
        "Runny nose and cough",
    ]
    picked = None
    for col, prompt in zip(quick_cols, quick_prompts):
        if col.button(prompt, width='stretch'):
            picked = prompt

    user_input = st.chat_input("Describe your symptoms…") or picked
    if user_input:
        st.session_state.chat.append({"role": "user", "text": user_input})
        verdict = triage_symptoms(user_input)
        st.session_state.chat.append({"role": "bot", "text": verdict.reply, "level": verdict.level})
        st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "⚕️ AI Health Assistance is an educational prototype and does not provide medical diagnosis. "
    "In emergencies, always contact local emergency services."
)
