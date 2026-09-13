"""
AI Health Assistance — Live Dashboard Prototype
================================================
Run:  streamlit run app.py

Visual-first dashboard: glance → understand → act.
Tabs: Vitals · Medication Reminders · AI Doctor (24/7) · Report Translator.
Stack: Streamlit + Plotly (all logic offline & deterministic).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

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
    Level.HEALTHY: ("#15803d", "🟢"),
    Level.CAUTION: ("#b45309", "🟡"),
    Level.URGENT: ("#b91c1c", "🔴"),
}
LEVEL_COLOR = {"Low": "#15803d", "Moderate": "#d97706", "Critical": "#dc2626"}
LEVEL_EMOJI = {"Low": "🟢", "Moderate": "🟡", "Critical": "🚨"}

# Two-word status for the vital cards — no sentences, just the verdict.
SHORT_STATUS = {
    Level.HEALTHY: "✅ Normal",
    Level.CAUTION: "⚠️ Watch",
    Level.URGENT: "🚨 Alert",
}

# Professional SVG status icons for the verdict banner — crisper than emoji.
ICON_CHECK = (
    '<svg width="46" height="46" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="10" fill="#16a34a"/>'
    '<path d="M7.8 12.4l2.6 2.6 5.8-6" stroke="white" stroke-width="2.3" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
ICON_WARN = (
    '<svg width="46" height="46" viewBox="0 0 24 24" fill="none">'
    '<path d="M12 3.2L22 20.2H2L12 3.2Z" fill="#d97706"/>'
    '<path d="M12 9.8v4.4" stroke="white" stroke-width="2.3" stroke-linecap="round"/>'
    '<circle cx="12" cy="17" r="1.3" fill="white"/></svg>'
)
ICON_ALERT = (
    '<svg width="46" height="46" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="10" fill="white"/>'
    '<path d="M12 6.6v6.6" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round"/>'
    '<circle cx="12" cy="16.9" r="1.5" fill="#dc2626"/></svg>'
)

# Giant banner content + professional tinted palette per verdict.
BANNER = {
    "Low": (ICON_CHECK, "ALL GOOD", "Everything is in the safe zone."),
    "Moderate": (ICON_WARN, "PAY ATTENTION", "Some readings are off — see a doctor soon."),
    "Critical": (ICON_ALERT, "EMERGENCY", "Get help now — call your local emergency number."),
}
BANNER_STYLE = {
    "Low": {"bg": "#f0fdf4", "border": "#bbf7d0", "accent": "#15803d", "text": "#14532d"},
    "Moderate": {"bg": "#fffbeb", "border": "#fde68a", "accent": "#d97706", "text": "#78350f"},
    "Critical": {"bg": "#dc2626", "border": "#b91c1c", "accent": "#ffffff", "text": "#ffffff"},
}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem;}
      .verdict {
        border-radius: 14px; padding: 16px 22px;
        display: flex; align-items: center; gap: 18px;
      }
      .verdict-word {font-size: 1.9rem; font-weight: 800; letter-spacing: .5px; line-height: 1.15;}
      .verdict-action {font-size: .98rem; opacity: .85;}
      .score-ring {
        border-radius: 50%; width: 92px; height: 92px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        flex-shrink: 0; font-weight: 800; line-height: 1;
      }
      .chip {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 999px; padding: 7px 14px; text-align: center;
        font-weight: 600; font-size: .9rem; color: #334155;
      }
      .vital-card {
        background: #fff; color: #0f172a; border-radius: 14px; padding: 14px 16px;
        border: 1px solid #e2e8f0; border-top: 4px solid #15803d;
      }
      .vital-value {font-size: 2.1rem; font-weight: 800; line-height: 1.1;}
      .vital-label {font-size: .82rem; font-weight: 600; color: #64748b;}
      .vital-status {font-size: .88rem; font-weight: 700; margin-top: 2px;}
      .tag {border-radius: 999px; padding: 3px 12px; font-size: .78rem; font-weight: 700; color: #fff; display: inline-block;}
      .med-card {
        background: #fff; color: #0f172a; border-radius: 14px; padding: 14px 16px;
        border: 1px solid #e2e8f0; border-left: 5px solid #2563eb;
      }
      .med-name {font-size: 1.15rem; font-weight: 700;}
      .med-meta {font-size: .92rem; font-weight: 600; color: #64748b; margin-top: 2px;}
      .lab-row {
        background: #fff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 14px;
        padding: 12px 16px; margin: 8px 0;
      }
      .lab-name {font-size: 1.15rem; font-weight: 700;}
      .lab-why {font-size: .9rem; margin-top: 4px; color: #475569;}
      .chat-user {background: #eff6ff; color: #0f172a; border-radius: 14px 14px 4px 14px; padding: 10px 14px; margin: 6px 40px 6px 0;}
      .chat-bot  {background: #fff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 14px 14px 14px 4px; padding: 12px 14px; margin: 6px 0 6px 40px;}
      .doc-online {
        width: 10px; height: 10px; border-radius: 50%; background: #22c55e;
        display: inline-block; margin-right: 8px;
        box-shadow: 0 0 0 rgba(34,197,94,.6); animation: pulse 1.6s infinite;
      }
      @keyframes pulse {
        0% {box-shadow: 0 0 0 0 rgba(34,197,94,.55);}
        70% {box-shadow: 0 0 0 9px rgba(34,197,94,0);}
        100% {box-shadow: 0 0 0 0 rgba(34,197,94,0);}
      }
      .stTabs [data-baseweb="tab"] {font-size: 1rem; font-weight: 600; gap: 6px;}
      @keyframes alarm-pulse {
        0%, 100% {background-color:#dc2626; box-shadow:0 0 0 0 rgba(220,38,38,.5);}
        50% {background-color:#b91c1c; box-shadow:0 0 0 12px rgba(220,38,38,0);}
      }
      .alarm-banner {
        border-radius:14px; padding:16px 22px; color:white;
        display:flex; align-items:center; gap:18px;
        animation: alarm-pulse 1.2s ease-in-out infinite;
      }
      .pill-timer {
        background:rgba(255,255,255,.2); border-radius:999px;
        padding:3px 12px; font-size:.85rem; font-weight:700;
      }
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

DEFAULT_MEDS = [
    {"id": 1, "name": "Metformin 500mg", "times": ["08:00", "20:00"], "icon": "💊", "taken": set(), "missed": set()},
    {"id": 2, "name": "Vitamin D3", "times": ["09:00"], "icon": "☀️", "taken": set(), "missed": set()},
    {"id": 3, "name": "Amlodipine 5mg", "times": ["21:00"], "icon": "🫀", "taken": set(), "missed": set()},
]

if "vitals" not in st.session_state:
    st.session_state.vitals = dict(DEFAULT_VITALS)
if "meds" not in st.session_state:
    st.session_state.meds = [dict(m) for m in DEFAULT_MEDS]
if "chat" not in st.session_state:
    st.session_state.chat = [
        {"role": "bot", "text": "👋 I'm your AI Doctor — online 24/7. Tell me what's wrong.", "level": None}
    ]
if "report" not in st.session_state:
    st.session_state.report = None
if "recovery" not in st.session_state:
    st.session_state.recovery = None
if "alarm_on" not in st.session_state:
    st.session_state.alarm_on = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def apply_scenario(**values: float) -> None:
    """Update vitals AND the slider widgets' own state (keeps them in sync)."""
    st.session_state.vitals.update(values)
    for key, value in values.items():
        st.session_state[f"s_{key}"] = float(value)


def _parse_hhmm(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def _med_state(med: dict, now: datetime) -> str:
    """Return 'taken' | 'due' | 'upcoming' | 'missed' for display."""
    today = now.date()
    if today in med["taken"]:
        return "taken"
    if today in med["missed"]:
        return "missed"
    for hhmm in med["times"]:
        due_dt = datetime.combine(today, _parse_hhmm(hhmm))
        if now >= due_dt:
            return "due"  # a dose time has passed today and not marked taken
    return "upcoming"


def _due_meds(meds: list[dict], now: datetime) -> list[tuple[dict, str]]:
    """Meds whose time has arrived today and are still unmarked → [(med, HH:MM)]."""
    due: list[tuple[dict, str]] = []
    for med in meds:
        if now.date() in med["taken"] or now.date() in med["missed"]:
            continue
        for hhmm in med["times"]:
            if now >= datetime.combine(now.date(), _parse_hhmm(hhmm)):
                due.append((med, hhmm))
                break
    return due


def dismiss_alarm() -> None:
    """Stop the alarm until a NEW dose becomes due (snooze-safe)."""
    st.session_state.alarm_on = False
    st.session_state.alarm_dismissed_for = tuple(sorted(m["id"] for m, _ in _due_meds(st.session_state.meds, datetime.now())))
    st.session_state.alarm_started_at = None


def _next_dose(meds: list[dict], now: datetime) -> tuple[str, str] | None:
    """Soonest upcoming dose across all meds → (name, HH:MM)."""
    best = None
    for med in meds:
        for hhmm in med["times"]:
            dt = datetime.combine(now.date(), _parse_hhmm(hhmm))
            if dt < now:
                dt += timedelta(days=1)  # tomorrow's dose
            if best is None or dt < best[0]:
                best = (dt, med["name"], hhmm)
    if best is None:
        return None
    dt, name, hhmm = best
    delta = dt - now
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes = rem // 60
    when = f"in {hours}h {minutes:02d}m" if hours else f"in {minutes} min"
    return name, f"{hhmm} ({when})"


def _add_months(d: date, months: int) -> date:
    """Date + N months, clamped to end-of-month when the day overflows."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _build_plan(start: date) -> list[dict]:
    """Follow-up schedule: status check at 1 month, cure check at 6 months.

    If the 6-month cure check fails, a +3-month re-check is appended
    dynamically (and repeats until cured).
    """
    return [
        {"months": 1, "due": _add_months(start, 1), "done": False, "outcome": None},
        {"months": 6, "due": _add_months(start, 6), "done": False, "outcome": None},
    ]


def _due_reviews(plan: list[dict], today: date) -> list[dict]:
    return [r for r in plan if not r["done"] and r["due"] <= today]


def _example_case(disease: str, medicine: str, started_days_ago: int, history: list[tuple[int, str]]) -> dict:
    """Pre-played recovery case for one-click demos.

    ``history`` is a list of (month, verdict) pairs already reviewed.
    Re-check entries are appended the same way the live form does.
    """
    start = date.today() - timedelta(days=started_days_ago)
    plan = _build_plan(start)
    hist: list[dict] = []
    status = "in_treatment"
    for months, verdict in history:
        review = next(r for r in plan if r["months"] == months and not r["done"])
        review["done"] = True
        review["outcome"] = verdict
        hist.append({"months": months, "on": _add_months(start, months), "verdict": verdict})
        if verdict == "Cured":
            status = "cured"
        elif months >= 6 or verdict == "Not cured":
            plan.append({"months": months + 3, "due": _add_months(review["due"], 3), "done": False, "outcome": None})
    return {
        "disease": disease,
        "medicine": medicine,
        "start": start,
        "plan": plan,
        "status": status,
        "history": hist,
    }


EXAMPLE_CASES = {
    "1️⃣ Month-1 check-up DUE": (
        "Type 2 Diabetes", "Metformin 500mg", 32, []
    ),
    "2️⃣ On track (started 10 days ago)": (
        "Hypertension (Stage 1)", "Amlodipine 5mg", 10, []
    ),
    "3️⃣ Month-6 cure check DUE": (
        "Hypothyroidism", "Levothyroxine 50mcg", 190, [(1, "Improving — continue medicine")]
    ),
    "4️⃣ Not cured → 3-month re-check DUE": (
        "Pulmonary Tuberculosis", "Anti-TB therapy (4-drug)", 305, [(1, "Improving — continue medicine"), (6, "Not cured")]
    ),
    "5️⃣ Already CURED (discharged)": (
        "Vitamin D Deficiency", "Cholecalciferol 60K IU weekly", 250, [(1, "Improving — continue medicine"), (6, "Cured")]
    ),
}


NOW = datetime.now()

# ---------------------------------------------------------------------------
# Medication ALARM — real sound, fires while the app is open
# ---------------------------------------------------------------------------
ALARM_MAX_SECONDS = 60  # ring for at most 1 minute, then auto-silence

if "alarm_dismissed_for" not in st.session_state:
    st.session_state.alarm_dismissed_for = ()
if "alarm_started_at" not in st.session_state:
    st.session_state.alarm_started_at = None

# Hands-free: the page re-checks the clock every 30 s so the alarm fires
# on its own while the app is open. Slight jitter avoids server stampedes.
if st.session_state.get("authenticated"):
    st_autorefresh(interval=30_000, key="alarm_clock_tick")

_alarm_due = _due_meds(st.session_state.meds, NOW)
_alarm_ids = tuple(sorted(m["id"] for m, _ in _alarm_due))
_new_alarm = bool(_alarm_due) and _alarm_ids != st.session_state.alarm_dismissed_for
if _new_alarm and st.session_state.alarm_started_at is None:
    st.session_state.alarm_started_at = NOW
_alarm_run = (NOW - st.session_state.alarm_started_at).total_seconds() if st.session_state.alarm_started_at else 0.0
_alarm_expired = _new_alarm and _alarm_run > ALARM_MAX_SECONDS
_alarm_sounding = _new_alarm and not _alarm_expired
if not _new_alarm:
    st.session_state.alarm_started_at = None  # dose handled → rearm timer
if _alarm_sounding:
    st.session_state.alarm_on = True


def _render_alarm() -> None:
    """Looping alarm song + pulsing red banner for every due dose."""
    st.markdown(
        f'''
        <div class="alarm-banner">
          <div style="font-size:2.6rem;">⏰</div>
          <div style="flex:1;">
            <div style="font-size:1.5rem; font-weight:900;">MEDICINE ALARM!</div>
            <div style="font-size:1rem; opacity:.95;">
              Time to take: <b>{" · ".join(m["icon"] + " " + m["name"] for m, _ in _alarm_due)}</b>
              &nbsp;<span class="pill-timer">due {" · ".join(t for _, t in _alarm_due)}</span>
            </div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.audio("assets/alarm.wav", autoplay=True, loop=True)
    d1, d2, _ = st.columns([1, 1, 2])
    d1.button("🔕 Dismiss", on_click=dismiss_alarm, width='stretch')

    def _take_all_due() -> None:
        now = datetime.now()
        for med, _t in _due_meds(st.session_state.meds, now):
            med["taken"].add(now.date())
            med["missed"].discard(now.date())
        dismiss_alarm()

    d2.button("✅ I took it", on_click=_take_all_due, width='stretch')
    st.write("")


if st.session_state.get("authenticated"):
    if _alarm_sounding:
        st.progress(min(1.0, _alarm_run / ALARM_MAX_SECONDS), text=f"🔔 Ringing — auto-silences in {max(0, ALARM_MAX_SECONDS - int(_alarm_run))}s")
        _render_alarm()
    elif _new_alarm and _alarm_expired:
        st.markdown(
            '<div class="chip" style="margin-bottom:4px;">🔕 Alarm silenced after 1 minute — medicine still due. Mark it in 💊 Medications.</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.meds:
        nxt = _next_dose(st.session_state.meds, NOW)
        if nxt:
            st.markdown(
                f'<div class="chip" style="margin-bottom:4px;">⏰ Alarm armed — next: {nxt[0]} at {nxt[1]}</div>',
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Authentication — local account store (hashed passwords, demo-grade)
# ---------------------------------------------------------------------------
USERS_FILE = Path(__file__).parent / "users.json"


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _load_users() -> dict:
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _login_success(name: str) -> None:
    st.session_state.authenticated = True
    st.session_state.who = name
    # Fresh, per-user workspace on every login.
    for key in ("vitals", "meds", "chat", "recovery", "report"):
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


def _render_auth() -> None:
    st.markdown('<div style="height:7vh"></div>', unsafe_allow_html=True)
    _l, mid, _r = st.columns([1, 1.7, 1])
    with mid:
        st.markdown(
            '<div style="text-align:center; padding:10px 0 2px;">'
            '<div style="font-size:3rem;">🩺</div>'
            '<div style="font-size:1.9rem; font-weight:800; color:#0f172a;">AI Health Assistance</div>'
            '<div style="font-size:.95rem; color:#64748b;">Your health, decoded — vitals, medicines, recovery & reports</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        tab_login, tab_signup = st.tabs(["Login", "Create account"])
        users = _load_users()

        with tab_login:
            with st.form("login_form", border=True):
                lu = st.text_input("Username", key="login_user")
                lp = st.text_input("Password", type="password", key="login_pw")
                if st.form_submit_button("Login", type="primary", width='stretch'):
                    user = users.get(lu.strip().lower())
                    if user and user["pw"] == _hash(lp):
                        _login_success(user["name"])
                    else:
                        st.error("❌ Wrong username or password — try again, or create an account.")

        with tab_signup:
            with st.form("signup_form", border=True):
                su_name = st.text_input("Full name", key="su_name")
                su_user = st.text_input("Choose a username", key="su_user")
                sp1 = st.text_input("Password", type="password", key="su_pw")
                sp2 = st.text_input("Confirm password", type="password", key="su_pw2")
                if st.form_submit_button("✅ Create account", type="primary", width='stretch'):
                    uname = su_user.strip().lower()
                    if not su_name.strip() or not uname:
                        st.error("Please fill your name and a username.")
                    elif len(sp1) < 4:
                        st.error("Password needs at least 4 characters.")
                    elif sp1 != sp2:
                        st.error("Passwords do not match.")
                    elif uname in users:
                        st.error("That username is taken — pick another.")
                    else:
                        users[uname] = {"name": su_name.strip(), "pw": _hash(sp1)}
                        _save_users(users)
                        _login_success(su_name.strip())

        st.caption("🔒 Demo sign-in — passwords are hashed and stored only on this device.")

        st.markdown(
            '<div style="display:flex; align-items:center; gap:10px; margin:6px 0;">'
            '<div style="flex:1; height:1px; background:#e2e8f0;"></div>'
            '<div style="font-size:.8rem; color:#94a3b8;">OR</div>'
            '<div style="flex:1; height:1px; background:#e2e8f0;"></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        google_svg = (
            '<svg width="18" height="18" viewBox="0 0 48 48">'
            '<path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z"/>'
            '<path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>'
            '<path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>'
            '<path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C36.9 39.2 44 34 44 24c0-1.3-.1-2.6-.4-3.9z"/>'
            '</svg>'
        )
        st.markdown(
            '<a href="?google=1" style="text-decoration:none;">'
            '<div style="display:flex; align-items:center; justify-content:center; gap:10px;'
            'background:white; border:1px solid #dadce0; border-radius:8px; padding:9px 0;'
            'font-family:Roboto,Arial,sans-serif; font-size:.95rem; font-weight:500; color:#3c4043;">'
            f'{google_svg}<span>Sign in with Google</span>'
            '</div></a>',
            unsafe_allow_html=True,
        )
        st.caption("⚡ Demo mode — one-click sign-in. Production wires Google OAuth 2.0 (see architecture doc).")


# Google demo sign-in: the styled button is a link to ?google=1 — a full
# page load with that param lands here and signs the demo user in.
if not st.session_state.get("authenticated") and st.query_params.get("google") == "1":
    _login_success("Google User")

if not st.session_state.get("authenticated"):
    _render_auth()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — demo controls + med quick-view
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🩺 AI Health")
    st.caption(f"👤 **{st.session_state.get('who', 'Guest')}**")
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
    nxt = _next_dose(st.session_state.meds, NOW)
    if nxt:
        st.markdown(f"⏰ **Next dose:** {nxt[0]} · {nxt[1]}")
    if st.button("🚪 Logout", width='stretch'):
        st.session_state.authenticated = False
        st.query_params.clear()
        st.rerun()
    rec = st.session_state.recovery
    if rec and rec["status"] == "cured":
        st.markdown("🎉 **Recovery:** Cured & discharged")
    elif rec:
        due = _due_reviews(rec["plan"], NOW.date())
        if due:
            st.markdown(f"🔔 **Recovery:** Month-{due[0]['months']} check-up DUE")
        else:
            nxt_r = next((r for r in rec["plan"] if not r["done"]), None)
            if nxt_r:
                st.markdown(f"🩹 **Recovery:** Month-{nxt_r['months']} on {nxt_r['due'].strftime('%d %b')}")
    st.caption("⚠️ Educational demo — not a medical device.")

# ---------------------------------------------------------------------------
# Giant verdict banner + quick chips
# ---------------------------------------------------------------------------
result = composite_triage(st.session_state.vitals)
icon, word, action = BANNER[result.level]
verdict_color = LEVEL_COLOR[result.level]
bstyle = BANNER_STYLE[result.level]

st.markdown(
    f"""
    <div class="verdict" style="background:{bstyle['bg']}; border:1px solid {bstyle['border']}; border-left:6px solid {bstyle['accent']};">
      <div style="line-height:1; display:flex; align-items:center;">{icon}</div>
      <div style="flex:1;">
        <div class="verdict-word" style="color:{bstyle['text']};">{word}</div>
        <div class="verdict-action" style="color:{bstyle['text']};">{action}</div>
      </div>
      <div class="score-ring" style="background:{bstyle['accent']}; color:{'#ffffff' if result.level != 'Critical' else '#dc2626'};">
        <span style="font-size:1.8rem;">{result.score}</span><span style="font-size:.8rem; opacity:.85;">/100</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="chip" style="background:#fff1f2; border-color:#fecdd3; color:#9f1239;">👀 Vitals live</div>', unsafe_allow_html=True)
with c2:
    nxt = _next_dose(st.session_state.meds, NOW)
    st.markdown(
        f'<div class="chip" style="background:#eff6ff; border-color:#bfdbfe; color:#1e40af;">⏰ Next pill: {nxt[1] if nxt else "none set"}</div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown('<div class="chip" style="background:#f0fdfa; border-color:#99f6e4; color:#115e59;">👨‍⚕️ AI Doctor online 24/7</div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="chip" style="background:#f5f3ff; border-color:#ddd6fe; color:#5b21b6;">📄 Lab jargon ➜ plain English</div>', unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_vitals, tab_meds, tab_doc, tab_recovery, tab_report = st.tabs(
    ["📡 Vitals", "💊 Medications", "👨‍⚕️ AI Doctor · 24/7", "🩺 Recovery Tracker", "📄 Report Translator"]
)

# === TAB 1 — VITALS =========================================================
with tab_vitals:
    left, right = st.columns([3, 2], gap="large")

    with left:
        # Controls FIRST so a slider move instantly re-renders the cards below.
        st.markdown("##### 🎛️ Vitals simulation")
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
                    tint = {Level.HEALTHY: "#f0fdf4", Level.CAUTION: "#fffbeb", Level.URGENT: "#fef2f2"}[level]
                    st.markdown(
                        f"""
                        <div class="vital-card" style="border-top-color:{color}; background:{tint};">
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
            <div class="verdict" style="background:#eff6ff; border:1px solid #bfdbfe; border-left:6px solid #2563eb; padding:12px 16px; gap:10px;">
              <div style="font-size:1.3rem;">➜</div>
              <div style="font-size:1.05rem; font-weight:700; color:#1e3a8a;">{first}</div>
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
            st.success("✅ All 6 vitals inside normal bands — nothing to worry about.")

        st.markdown("##### 📈 Last 24 hours")
        trend_fig = go.Figure()
        hours = list(range(24))
        # Deterministic wobble so the demo chart never flickers between reruns.
        wobble = [0, 1.5, -1, 2, -2.5, 1, 0.5, -1.5, 2.5, -2, 0, 1,
                  -1, 2, 0.5, -2.5, 1.5, 0, -1, 1, 2, -1.5, 0.5, -0.5]
        for key, name, color in [
            ("heart_rate", "Heart Rate", "#dc2626"),
            ("spo2", "SpO₂", "#3b82f6"),
        ]:
            base = st.session_state.vitals[key]
            series = [round(base + w, 1) for w in wobble]
            trend_fig.add_trace(go.Scatter(x=hours, y=series, name=name, line={"color": color, "width": 3}))
        trend_fig.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(trend_fig, width='stretch')

# === TAB 2 — MEDICATION REMINDERS ===========================================
with tab_meds:
    now_med = datetime.now()
    nxt = _next_dose(st.session_state.meds, now_med)

    # Headline: next dose countdown — the thing you glance at.
    if nxt:
        st.markdown(
            f"""
            <div class="verdict" style="background:#eff6ff; border:1px solid #bfdbfe; border-left:6px solid #2563eb;">
              <div style="font-size:2.2rem; line-height:1;">⏰</div>
              <div style="flex:1;">
                <div class="verdict-word" style="color:#1e3a8a;">NEXT DOSE</div>
                <div class="verdict-action" style="color:#334155;">{nxt[0]} at {nxt[1]}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.write("")

    add_col, list_col = st.columns([1, 3], gap="large")

    with add_col:
        st.markdown("##### ➕ Add medicine")
        m_name = st.text_input("Medicine name", placeholder="e.g. Paracetamol 650mg")
        m_times = st.multiselect(
            "Times per day",
            options=[f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)],
            default=["08:00"],
        )
        m_icon = st.selectbox("Icon", ["💊", "🫀", "☀️", "💉", "🧪", "🩹"])
        if st.button("➕ Add", type="primary", width='stretch') and m_name.strip() and m_times:
            new_id = max((m["id"] for m in st.session_state.meds), default=0) + 1
            st.session_state.meds.append(
                {"id": new_id, "name": m_name.strip(), "times": sorted(m_times), "icon": m_icon, "taken": set(), "missed": set()}
            )
            st.rerun()

    with list_col:
        st.markdown("##### 💊 Today's schedule")
        if not st.session_state.meds:
            st.info("No medicines yet — add one on the left.")
        now_m = datetime.now()
        for med in st.session_state.meds:
            state = _med_state(med, now_m)
            edge = {"taken": "#15803d", "due": "#d97706", "missed": "#dc2626", "upcoming": "#2563eb"}[state]
            tint = {"taken": "#f0fdf4", "due": "#fffbeb", "missed": "#fef2f2", "upcoming": "#eff6ff"}[state]
            badge = {
                "taken": '<span class="tag" style="background:#15803d;">✅ TAKEN</span>',
                "due": '<span class="tag" style="background:#d97706;">⏰ DUE NOW</span>',
                "missed": '<span class="tag" style="background:#dc2626;">❌ MISSED</span>',
                "upcoming": '<span class="tag" style="background:#2563eb;">🕒 SCHEDULED</span>',
            }[state]
            times_text = " · ".join(med["times"])
            st.markdown(
                f"""
                <div class="med-card" style="border-left-color:{edge}; background:{tint};">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="med-name">{med["icon"]} {med["name"]}</div>
                    {badge}
                  </div>
                  <div class="med-meta">🕒 {times_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2, _ = st.columns([1, 1, 2])
            if b1.button("✅ Taken", key=f"take_{med['id']}", width='stretch', on_click=dismiss_alarm):
                med["taken"].add(now_m.date())
                med["missed"].discard(now_m.date())
                st.rerun()
            if b2.button("❌ Skip", key=f"skip_{med['id']}", width='stretch', on_click=dismiss_alarm):
                med["missed"].add(now_m.date())
                med["taken"].discard(now_m.date())
                st.rerun()

        # Adherence ring: taken vs missed vs scheduled today.
        total_doses = sum(len(m["times"]) for m in st.session_state.meds)
        done_doses = sum(1 for m in st.session_state.meds if now_m.date() in m["taken"])
        pct = int(100 * done_doses / total_doses) if total_doses else 100
        st.markdown("##### 📊 Today's adherence")
        a1, a2 = st.columns([1, 2])
        with a1:
            adh = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    number={"suffix": "%", "font": {"size": 34}},
                    gauge={
                        "axis": {"range": [0, 100], "showticklabels": False},
                        "bar": {"color": "#15803d" if pct >= 80 else "#d97706" if pct >= 50 else "#dc2626", "thickness": 0.3},
                        "steps": [
                            {"range": [0, 50], "color": "rgba(220,38,38,.25)"},
                            {"range": [50, 80], "color": "rgba(245,158,11,.25)"},
                            {"range": [80, 100], "color": "rgba(22,163,74,.30)"},
                        ],
                    },
                )
            )
            adh.update_layout(height=180, margin=dict(t=10, b=10, l=20, r=20))
            st.plotly_chart(adh, width='stretch')
        with a2:
            st.markdown(
                f'<div class="chip" style="font-size:1rem;">✅ {done_doses} of {total_doses} doses taken today</div>',
                unsafe_allow_html=True,
            )

# === TAB 3 — AI DOCTOR 24/7 =================================================
with tab_doc:
    st.markdown(
        """
        <div class="verdict" style="background:#f0fdfa; border:1px solid #99f6e4; border-left:6px solid #0d9488;">
          <div style="font-size:2.2rem; line-height:1;">🩺</div>
          <div style="flex:1;">
            <div class="verdict-word" style="font-size:1.6rem; color:#134e4a;">AI DOCTOR <span class="doc-online"></span> ONLINE</div>
            <div class="verdict-action" style="color:#334155;">Available 24 hours · 7 days · no appointment needed</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    d_left, d_right = st.columns([3, 2], gap="large")
    with d_left:
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
            if col.button(prompt, key=f"doc_{prompt}", width='stretch'):
                picked = prompt

        user_input = st.chat_input("Type your symptoms — the doctor never sleeps…") or picked
        if user_input:
            st.session_state.chat.append({"role": "user", "text": user_input})
            verdict = triage_symptoms(user_input)
            st.session_state.chat.append({"role": "bot", "text": verdict.reply, "level": verdict.level})
            st.rerun()

    with d_right:
        st.markdown("##### 🕐 Always-on availability")
        for label, sub in [
            ("🌙 Midnight", "Online"),
            ("🌅 Early morning", "Online"),
            ("☀️ Afternoon", "Online"),
            ("🌙 Late night", "Online"),
        ]:
            st.markdown(f"- <span class='doc-online'></span> **{label}** — {sub}", unsafe_allow_html=True)
        st.markdown("##### 🚨 Escalation built-in")
        st.markdown("- Red-flag symptoms flip the chat to **CRITICAL RISK** instantly.")
        st.markdown("- Verdicts come from the same explainable triage engine as the Vitals tab.")

# === TAB 4 — RECOVERY TRACKER ===============================================
with tab_recovery:
    rec = st.session_state.recovery
    clock = st.session_state.get("clock", date.today())

    # -- No active case → enrollment form ------------------------------------
    if rec is None:
        st.markdown(
            '<div class="verdict" style="background:#f5f3ff; border:1px solid #ddd6fe; border-left:6px solid #7c3aed;">'
            '<div style="font-size:2.2rem; line-height:1;">🩺</div>'
            '<div style="flex:1;"><div class="verdict-word" style="color:#4c1d95;">RECOVERY TRACKER</div>'
            '<div class="verdict-action" style="color:#334155;">Start a treatment → automatic check-ups at 1 & 6 months → cured? discharged. Not cured? re-checked every 3 months.</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        with st.form("enroll_form", border=False):
            e1, e2 = st.columns(2)
            disease = e1.text_input("🦠 Disease / condition", placeholder="e.g. Type 2 Diabetes")
            medicine = e2.text_input("💊 Medicine prescribed", placeholder="e.g. Metformin 500mg")
            start = st.date_input("📅 Treatment start date", value=date.today())
            if st.form_submit_button("🚀 Start recovery plan", type="primary") and disease.strip() and medicine.strip():
                st.session_state.recovery = {
                    "disease": disease.strip(),
                    "medicine": medicine.strip(),
                    "start": start,
                    "plan": _build_plan(start),
                    "status": "in_treatment",
                    "history": [],
                }
                st.session_state.clock = date.today()
                st.rerun()
        st.info("👆 The plan schedules a **month-1 status check** and a **month-6 cure check** automatically.")

        with st.expander("🧪 Load an example case (one-click demo)"):
            st.caption("Five pre-played cases — each lands at a different moment of the recovery loop.")
            ex_cols = st.columns(2)
            for i, (label, (disease, medicine, days, history)) in enumerate(EXAMPLE_CASES.items()):
                if ex_cols[i % 2].button(label, width='stretch'):
                    st.session_state.recovery = _example_case(disease, medicine, days, history)
                    st.session_state.clock = date.today()
                    st.rerun()

    else:
        due_reviews = _due_reviews(rec["plan"], clock)

        # -- Notification banner -------------------------------------------
        if rec["status"] == "cured":
            months = rec["history"][-1]["months"] if rec["history"] else 6
            st.markdown(
                f'<div class="verdict" style="background:#f0fdf4; border:1px solid #bbf7d0; border-left:6px solid #15803d;">'
                f'<div style="font-size:2.2rem;">🎉</div>'
                f'<div style="flex:1;"><div class="verdict-word" style="color:#14532d;">CURED & DISCHARGED</div>'
                f'<div class="verdict-action" style="color:#166534;">{rec["disease"]} — treatment complete after {months} months. No further check-ups needed.</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif due_reviews:
            r = due_reviews[0]
            st.markdown(
                f'<div class="verdict" style="background:#fffbeb; border:1px solid #fde68a; border-left:6px solid #d97706;">'
                f'<div style="font-size:2.2rem;">🔔</div>'
                f'<div style="flex:1;"><div class="verdict-word" style="color:#78350f;">CHECK-UP DUE — MONTH {r["months"]}</div>'
                f'<div class="verdict-action" style="color:#92400e;">How is your {rec["disease"]} treatment going? Record your status below.</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            nxt_r = next((r for r in rec["plan"] if not r["done"]), None)
            if nxt_r:
                days = (nxt_r["due"] - clock).days
                st.markdown(
                    f'<div class="verdict" style="background:#eff6ff; border:1px solid #bfdbfe; border-left:6px solid #2563eb;">'
                    f'<div style="font-size:2.2rem;">🗓️</div>'
                    f'<div style="flex:1;"><div class="verdict-word" style="color:#1e3a8a;">ON TRACK</div>'
                    f'<div class="verdict-action" style="color:#334155;">{rec["disease"]} · next check-up: month {nxt_r["months"]} on {nxt_r["due"].strftime("%d %b %Y")} (in {days} days)</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.write("")

        # -- Timeline cards -------------------------------------------------
        st.markdown("##### 🗺️ Recovery timeline")
        plan_sorted = sorted(rec["plan"], key=lambda r: r["due"])
        tcols = st.columns(min(len(plan_sorted), 4))
        for i, r in enumerate(plan_sorted):
            with tcols[i % len(tcols)]:
                if r["done"]:
                    state_icon, tint, edge, verdict_text = "✅", "#f0fdf4", "#15803d", f"{r['outcome']}"
                elif r["due"] <= clock:
                    state_icon, tint, edge, verdict_text = "🔔", "#fffbeb", "#d97706", "DUE NOW"
                else:
                    state_icon, tint, edge, verdict_text = "🕒", "#eff6ff", "#2563eb", r["due"].strftime("%d %b")
                st.markdown(
                    f'<div class="med-card" style="border-left-color:{edge}; background:{tint}; padding:10px 12px;">'
                    f'<div class="med-name" style="font-size:1rem;">{state_icon} Month {r["months"]}</div>'
                    f'<div class="med-meta">{verdict_text}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.write("")

        # -- Cure check form (only when a review is due) ---------------------
        if rec["status"] != "cured" and due_reviews:
            r = due_reviews[0]
            with st.form(f"cure_form_{r['months']}", border=False):
                st.markdown(f"##### 📋 Month-{r['months']} review — {r['due'].strftime('%d %b %Y')}")
                c1, c2 = st.columns(2)
                symptoms = c1.radio("Did the symptoms go away?", ["Yes, fully", "Partially", "No, same or worse"])
                labs = c2.radio("Latest lab reports normal?", ["Yes, all normal", "Some abnormal", "Not tested yet"])
                doctor = st.radio("Doctor's assessment", ["Cured", "Improving — continue medicine", "Not cured"])
                if st.form_submit_button("Submit review", type="primary"):
                    r["done"] = True
                    r["outcome"] = doctor
                    rec["history"].append({"months": r["months"], "on": clock, "verdict": doctor})
                    if doctor == "Cured":
                        rec["status"] = "cured"
                    elif r["months"] >= 6 or doctor == "Not cured":
                        recheck_due = _add_months(r["due"], 3)
                        rec["plan"].append({
                            "months": r["months"] + 3,
                            "due": recheck_due,
                            "done": False,
                            "outcome": None,
                        })
                    st.rerun()
        elif rec["status"] != "cured":
            st.info("🗓️ Nothing to fill right now — the next check-up will notify you automatically.")

        # -- History log ------------------------------------------------------
        if rec["history"]:
            st.markdown("##### 📜 Review history")
            for h in rec["history"]:
                icon = "🎉" if h["verdict"] == "Cured" else "📈" if h["verdict"].startswith("Improving") else "⚠️"
                st.markdown(f"- {icon} **Month {h['months']}** ({h['on'].strftime('%d %b %Y')}): {h['verdict']}")

            st.divider()
            st.caption("🔔 Alarm test")
            if st.button("▶️ Play alarm song (test)", width='stretch'):
                st.session_state.alarm_test = True
            if st.session_state.pop("alarm_test", False):
                st.audio("assets/alarm.wav", autoplay=True)
                st.toast("🔔 This is the medicine alarm sound!")

        # -- Demo time-travel -------------------------------------------------
        with st.expander("⏩ Demo time-travel (for judges)"):
            st.caption("Simulate months passing — watch the notifications fire.")
            t1, t2, t3 = st.columns(3)
            if t1.button("+1 month", width='stretch'):
                st.session_state.clock = clock + timedelta(days=31)
                st.rerun()
            if t2.button("+6 months", width='stretch'):
                st.session_state.clock = clock + timedelta(days=183)
                st.rerun()
            if t3.button("Reset to today", width='stretch'):
                st.session_state.clock = date.today()
                st.rerun()
            if st.button("🗑️ Discharge & start a new case", width='stretch'):
                st.session_state.recovery = None
                st.session_state.clock = date.today()
                st.rerun()
            st.divider()
            st.caption("Or jump straight into a different story:")
            ex_cols2 = st.columns(2)
            for i, (label, (disease, medicine, days, history)) in enumerate(EXAMPLE_CASES.items()):
                if ex_cols2[i % 2].button(label, key=f"swap_{i}", width='stretch'):
                    st.session_state.recovery = _example_case(disease, medicine, days, history)
                    st.session_state.clock = date.today()
                    st.rerun()

# === TAB 5 — REPORT TRANSLATOR ==============================================
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

    if st.button("🧪 Load sample lab report (one-click demo)", width='stretch'):
        sample_path = Path(__file__).parent / "samples" / "sample_report.txt"
        st.session_state.report = translate_report(sample_path.read_text(encoding="utf-8"))

    if st.session_state.report:
        rep = st.session_state.report
        n_ab, n_all = len(rep["abnormal"]), len(rep["results"])
        if n_ab == 0 and n_all:
            banner = '<div class="verdict" style="background:#f0fdf4; border:1px solid #bbf7d0; border-left:6px solid #15803d;"><div style="font-size:2rem;">✅</div><div class="verdict-word" style="color:#14532d;">ALL CLEAR</div><div class="verdict-action" style="color:#166534;">Every marker is inside the normal range.</div></div>'
        elif n_all:
            banner = f'<div class="verdict" style="background:#fffbeb; border:1px solid #fde68a; border-left:6px solid #d97706;"><div style="font-size:2rem;">📋</div><div class="verdict-word" style="color:#78350f;">{n_ab} of {n_all} NEED A LOOK</div><div class="verdict-action" style="color:#92400e;">Each line below shows what it means.</div></div>'
        else:
            banner = '<div class="verdict" style="background:#fff; border:1px solid #e2e8f0; border-left:6px solid #64748b;"><div class="verdict-action" style="color:#334155;">No known lab markers found — try the sample text.</div></div>'
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

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("⚕️ Educational prototype — not medical advice. In an emergency, call your local emergency number.")
