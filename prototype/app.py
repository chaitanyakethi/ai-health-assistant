"""
AI Health Assistance — Live Dashboard Prototype
================================================
Run:  streamlit run app.py

Visual-first dashboard: glance → understand → act.
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
LEVEL_EMOJI = {"Low": "🟢", "Moderate": "🟡", "Critical": "🚨"}

# Two-word status for the vital cards — no sentences, just the verdict.
SHORT_STATUS = {
    Level.HEALTHY: "✅ Normal",
    Level.CAUTION: "⚠️ Watch",
    Level.URGENT: "🚨 Alert",
}

# Giant banner content per overall verdict.
BANNER = {
    "Low": ("🟢", "ALL GOOD", "Everything is in the safe zone. Keep it up! 💪"),
    "Moderate": ("🟡", "PAY ATTENTION", "Some readings are off — see a doctor soon. 📅"),
    "Critical": ("🚨", "EMERGENCY", "Get help NOW — call your local emergency number."),
}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem;}
      .verdict {
        border-radius: 20px; padding: 18px 26px; color: white;
        display: flex; align-items: center; gap: 22px;
        box-shadow: 0 8px 24px rgba(15,23,42,.18);
      }
      .verdict-word {font-size: 2.7rem; font-weight: 900; letter-spacing: 1px; line-height: 1.1;}
      .verdict-action {font-size: 1.05rem; opacity: .95;}
      .score-ring {
        background: rgba(255,255,255,.18); border-radius: 50%;
        width: 108px; height: 108px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; flex-shrink: 0;
        font-weight: 800; line-height: 1;
      }
      .chip {
        background: white; border: 1px solid rgba(148,163,184,.35);
        border-radius: 999px; padding: 8px 16px; text-align: center;
        font-weight: 700; font-size: .95rem; color: #0f172a;
        box-shadow: 0 1px 3px rgba(15,23,42,.06);
      }
      .vital-card {
        background: white; color: #0f172a; border-radius: 16px; padding: 14px 16px;
        border: 1px solid rgba(148,163,184,.28); border-top: 5px solid #16a34a;
        box-shadow: 0 2px 6px rgba(15,23,42,.06);
      }
      .vital-value {font-size: 2.3rem; font-weight: 900; line-height: 1.1;}
      .vital-label {font-size: .85rem; font-weight: 700; opacity: .8;}
      .vital-status {font-size: .9rem; font-weight: 800; margin-top: 2px;}
      .tag {border-radius: 999px; padding: 3px 12px; font-size: .8rem; font-weight: 800; color: white; display: inline-block;}
      .chat-user {background: #dbeafe; border-radius: 14px 14px 4px 14px; padding: 10px 14px; margin: 6px 40px 6px 0;}
      .chat-bot  {background: white; color: #0f172a; border: 1px solid rgba(148,163,184,.3); border-radius: 14px 14px 14px 4px; padding: 12px 14px; margin: 6px 0 6px 40px; box-shadow: 0 1px 3px rgba(15,23,42,.06);}
      .lab-row {
        background: white; color: #0f172a; border: 1px solid rgba(148,163,184,.28); border-radius: 14px;
        padding: 12px 16px; margin: 8px 0; box-shadow: 0 1px 3px rgba(15,23,42,.06);
      }
      .lab-name {font-size: 1.2rem; font-weight: 900;}
      .lab-why {font-size: .9rem; margin-top: 4px; color: #334155;}
      .stTabs [data-baseweb="tab"] {font-size: 1.05rem; font-weight: 700; gap: 6px;}
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
        {"role": "bot", "text": "👋 Tell me how you feel — I'll tell you how urgent it is.", "level": None}
    ]
if "report" not in st.session_state:
    st.session_state.report = None

# ---------------------------------------------------------------------------
# Sidebar — 3 big demo buttons
# ---------------------------------------------------------------------------
def apply_scenario(**values: float) -> None:
    """Update vitals AND the slider widgets' own state (keeps them in sync)."""
    st.session_state.vitals.update(values)
    for key, value in values.items():
        st.session_state[f"s_{key}"] = float(value)


with st.sidebar:
    st.title("🩺 AI Health")
    st.caption("**See it. Understand it. Act fast.**")
    st.divider()
    st.subheader("One-click demos")
    if st.button("🚨 Emergency", width='stretch', type="primary"):
        apply_scenario(
            heart_rate=122.0, spo2=87.0, systolic=185.0, diastolic=115.0, temperature=101.8, sleep=4.0
        )
        st.rerun()
    if st.button("⚠️ Watch-list", width='stretch'):
        apply_scenario(
            heart_rate=104.0, spo2=93.0, systolic=138.0, diastolic=88.0, temperature=100.2, sleep=5.5
        )
        st.rerun()
    if st.button("✅ Healthy", width='stretch'):
        apply_scenario(**DEFAULT_VITALS)
        st.rerun()
    st.divider()
    st.caption("⚠️ Educational demo — not a medical device.")

# ---------------------------------------------------------------------------
# Giant verdict banner + 3 "what is this" chips
# ---------------------------------------------------------------------------
result = composite_triage(st.session_state.vitals)
emoji, word, action = BANNER[result.level]
verdict_color = LEVEL_COLOR[result.level]

st.markdown(
    f"""
    <div class="verdict" style="background: linear-gradient(120deg, {verdict_color}, {verdict_color}cc);">
      <div style="font-size:3.6rem; line-height:1;">{emoji}</div>
      <div style="flex:1;">
        <div class="verdict-word">{word}</div>
        <div class="verdict-action">{action}</div>
      </div>
      <div class="score-ring"><span style="font-size:2.1rem;">{result.score}</span><span style="font-size:.85rem; opacity:.85;">/ 100</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="chip">👀 &nbsp;Vitals at a glance</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="chip">📄 &nbsp;Lab jargon ➜ plain English</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="chip">💬 &nbsp;Symptoms ➜ next step</div>', unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_vitals, tab_report, tab_chat = st.tabs(
    ["📡 Vitals", "📄 Report Translator", "💬 Symptom Chat"]
)

# === TAB 1 — VITALS =========================================================
with tab_vitals:
    left, right = st.columns([3, 2], gap="large")

    with left:
        # Controls FIRST so a slider move instantly re-renders the cards below.
        st.markdown("##### 🎛️ Drag the sliders — watch the verdict change")
        slider_cols = st.columns(3)
        # All-float bounds/steps keep Streamlit's slider type rules happy.
        spans = {
            "heart_rate": (30.0, 190.0, "❤️ Heart rate"),
            "spo2": (70.0, 100.0, "🫁 Oxygen (SpO₂)"),
            "systolic": (70.0, 200.0, "⚡ BP top"),
            "diastolic": (40.0, 130.0, "⚡ BP bottom"),
            "temperature": (93.0, 106.0, "🌡️ Temperature"),
            "sleep": (0.0, 12.0, "😴 Sleep"),
        }
        for i, (key, (lo, hi, name)) in enumerate(spans.items()):
            with slider_cols[i % 3]:
                fractional = key in ("temperature", "sleep", "spo2")
                st.session_state.vitals[key] = st.slider(
                    name,
                    lo,
                    hi,
                    float(st.session_state.vitals[key]),
                    step=0.1 if fractional else 1.0,
                    format="%.1f" if fractional else "%d",
                    key=f"s_{key}",
                )

        st.markdown("##### &nbsp;")
        keys = list(VITAL_RANGES.keys())
        for row_start in range(0, len(keys), 2):
            cols = st.columns(2)
            for col, key in zip(cols, keys[row_start : row_start + 2]):
                value = st.session_state.vitals[key]
                _, _, _, _, unit, label = VITAL_RANGES[key]
                level, _ = assess_vital(value, key)
                color, _ = STATUS_COLOR[level]
                with col:
                    st.markdown(
                        f"""
                        <div class="vital-card" style="border-top-color:{color};">
                          <div class="vital-label">{label}</div>
                          <div class="vital-value" style="color:{color};">{value:g}
                            <span style="font-size:.95rem; opacity:.55; font-weight:600;">{unit}</span></div>
                          <div class="vital-status" style="color:{color};">{SHORT_STATUS[level]}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write("")

    with right:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=result.score,
                number={"suffix": "", "font": {"size": 44}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 0, "showticklabels": False},
                    "bar": {"color": verdict_color, "thickness": 0.28},
                    "steps": [
                        {"range": [0, 35], "color": "rgba(22,163,74,.30)"},
                        {"range": [35, 65], "color": "rgba(245,158,11,.30)"},
                        {"range": [65, 100], "color": "rgba(220,38,38,.35)"},
                    ],
                },
            )
        )
        fig.update_layout(height=250, margin=dict(t=10, b=10, l=25, r=25))
        st.plotly_chart(fig, width='stretch')

        # ONE big action + two short follow-ups. No paragraphs.
        first, *rest = result.recommendations
        st.markdown(
            f"""
            <div class="verdict" style="background:{verdict_color}; padding:14px 18px; gap:12px;">
              <div style="font-size:1.7rem;">➜</div>
              <div style="font-size:1.15rem; font-weight:800;">{first}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for rec in rest:
            st.markdown(f"- {rec}")

        healthy_flags = [f for f in result.flags if f[1] is not Level.HEALTHY]
        if healthy_flags:
            with st.expander("🔍 Why? (tap to expand)"):
                for key, level, reason in healthy_flags:
                    _, dot = STATUS_COLOR[level]
                    st.markdown(f"- {dot} {reason}")
        else:
            st.success("✅ All 6 vitals inside normal bands — nothing to explain, nothing to worry about.")

        st.markdown("##### 📈 Last 24 hours")
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
            trend_fig.add_trace(go.Scatter(x=hours, y=series, name=name, line={"color": color, "width": 3}))
        trend_fig.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(trend_fig, width='stretch')

# === TAB 2 — REPORT TRANSLATOR ==============================================
with tab_report:
    st.markdown("##### 🧾 Lab report ➜ 💬 plain English")

    up_left, up_right = st.columns(2)
    with up_left:
        uploaded = st.file_uploader("📤 Upload PDF / TXT", type=["pdf", "txt"])
        if uploaded is not None and st.button("✨ Decode report", type="primary", width='stretch'):
            st.session_state.report = translate_report(uploaded)
    with up_right:
        sample = st.text_area(
            "…or paste report text",
            height=110,
            placeholder="Hemoglobin 10.2 g/dL\nFasting Glucose 128 mg/dL\nTSH 6.1 µIU/mL",
        )
        if st.button("✨ Decode pasted text", width='stretch') and sample.strip():
            st.session_state.report = translate_report(sample)

    if st.session_state.report:
        rep = st.session_state.report
        n_ab, n_all = len(rep["abnormal"]), len(rep["results"])
        if n_ab == 0 and n_all:
            banner = '<div class="verdict" style="background:#16a34a; padding:14px 20px; gap:14px;"><div style="font-size:2.4rem;">🎉</div><div class="verdict-word" style="font-size:1.8rem;">ALL CLEAR</div><div class="verdict-action">Every marker is inside the normal range.</div></div>'
        elif n_all:
            banner = f'<div class="verdict" style="background:#f59e0b; padding:14px 20px; gap:14px;"><div style="font-size:2.4rem;">📋</div><div class="verdict-word" style="font-size:1.8rem;">{n_ab} of {n_all} NEED A LOOK</div><div class="verdict-action">Tap each line below to see what it means.</div></div>'
        else:
            banner = '<div class="verdict" style="background:#64748b; padding:14px 20px;"><div class="verdict-action">🤔 No known lab markers found — try the sample text on the right.</div></div>'
        st.markdown(banner, unsafe_allow_html=True)

        for r in rep["results"]:
            emoji = {"Normal": "✅", "High": "🔺", "Low": "🔻"}[r.status]
            color = {"Normal": "#16a34a", "High": "#dc2626", "Low": "#f59e0b"}[r.status]
            st.markdown(
                f"""
                <div class="lab-row">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="lab-name">{emoji} {r.analyte} &nbsp;<span style="font-weight:700; opacity:.6; font-size:1rem;">{r.value:g} {r.unit}</span></div>
                    <span class="tag" style="background:{color};">{r.status.upper()}</span>
                  </div>
                  <div class="lab-why">💬 {r.why}</div>
                  <div style="font-size:.78rem; opacity:.55; margin-top:2px;">Normal range: {r.range_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if rep["abnormal"]:
            st.warning(
                "📅 " + " · ".join(f"**{r.analyte}** {r.status.lower()}" for r in rep["abnormal"])
                + " — bring this summary to your doctor."
            )
    else:
        st.caption("👆 Upload or paste a report — results appear here instantly.")

# === TAB 3 — SYMPTOM CHAT ===================================================
with tab_chat:
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 <b>You:</b> {msg["text"]}</div>', unsafe_allow_html=True)
        else:
            level = msg.get("level")
            if level:
                pill = (
                    f'<span class="tag" style="background:{LEVEL_COLOR[level]}; font-size:.9rem; '
                    f'padding:4px 14px;">{LEVEL_EMOJI[level]} {level.upper()} RISK</span>'
                )
            else:
                pill = ""
            st.markdown(
                f'<div class="chat-bot">🩺 {pill}<br><br>{msg["text"]}</div>',
                unsafe_allow_html=True,
            )

    quick_cols = st.columns(4)
    quick_prompts = [
        "🚨 Crushing chest pain",
        "🌡️ Mild fever since yesterday",
        "😵 Tired and dizzy for a week",
        "🤧 Runny nose and cough",
    ]
    picked = None
    for col, prompt in zip(quick_cols, quick_prompts):
        if col.button(prompt, width='stretch'):
            picked = prompt

    user_input = st.chat_input("Type your symptoms…") or picked
    if user_input:
        st.session_state.chat.append({"role": "user", "text": user_input})
        verdict = triage_symptoms(user_input)
        st.session_state.chat.append({"role": "bot", "text": verdict.reply, "level": verdict.level})
        st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("⚕️ Educational prototype — not medical advice. In an emergency, call your local emergency number.")
