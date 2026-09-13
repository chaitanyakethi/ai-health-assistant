"""
Full button/widget audit for app.py — clicks every interactive control
across all tabs and asserts nothing raises.
Run:  python test_buttons_audit.py
"""

from __future__ import annotations

from datetime import date

from streamlit.testing.v1 import AppTest

RESULTS: list[tuple[str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append((name, "PASS"))
        print(f"PASS: {name}")
    except Exception as exc:  # noqa: BLE001 - audit collects all failures
        RESULTS.append((name, f"FAIL: {exc!r}"))
        print(f"FAIL: {name} -> {exc!r}")


def fresh() -> AppTest:
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception, f"page exception: {at.exception}"
    return at


def authed() -> AppTest:
    """Fresh session that actually LOGS IN as the audit user."""
    a = fresh()
    [t for t in a.text_input if t.label == "Username"][0].set_value("audit_user").run(timeout=30)
    [t for t in a.text_input if t.label == "Password"][0].set_value("audit1234").run(timeout=30)
    btn(a, "Login").set_value(True).run(timeout=30)
    assert not a.exception
    assert is_authed(a), "login failed in authed()"
    return a


def btn(a: AppTest, contains: str, idx: int = 0):
    matches = [b for b in a.button if b.label and contains in b.label]
    assert matches, f"button {contains!r} not found"
    return matches[idx]


def is_authed(a: AppTest) -> bool:
    return "authenticated" in a.session_state and a.session_state["authenticated"]


# ============================ LOGIN / AUTH ==================================
def t_login_rejects_wrong_password() -> None:
    a = fresh()
    [t for t in a.text_input if t.label == "Username"][0].set_value("nobody_here").run(timeout=30)
    [t for t in a.text_input if t.label == "Password"][0].set_value("x").run(timeout=30)
    btn(a, "Login").set_value(True).run(timeout=30)
    assert not is_authed(a)
    assert a.error, "expected an error message"


check("login: wrong password rejected with error", t_login_rejects_wrong_password)


def t_signup_mismatch_rejected() -> None:
    a = fresh()
    [t for t in a.text_input if t.label == "Full name"][0].set_value("Mismatch").run(timeout=30)
    [t for t in a.text_input if t.label == "Choose a username"][0].set_value("mismatch1").run(timeout=30)
    [t for t in a.text_input if t.label == "Password"][-1].set_value("abcd1234").run(timeout=30)
    [t for t in a.text_input if t.label == "Confirm password"][0].set_value("different").run(timeout=30)
    btn(a, "Create account").set_value(True).run(timeout=30)
    assert not is_authed(a)
    assert a.error


check("signup: mismatched passwords rejected", t_signup_mismatch_rejected)


# ============================ SETUP A USER ==================================
def t_signup_login() -> AppTest:
    import time as _time

    unique = f"audit_{int(_time.time())}"
    a = fresh()
    [t for t in a.text_input if t.label == "Full name"][0].set_value("Audit User").run(timeout=30)
    [t for t in a.text_input if t.label == "Choose a username"][0].set_value(unique).run(timeout=30)
    [t for t in a.text_input if t.label == "Password"][-1].set_value("audit1234").run(timeout=30)
    [t for t in a.text_input if t.label == "Confirm password"][0].set_value("audit1234").run(timeout=30)
    btn(a, "Create account").set_value(True).run(timeout=30)
    assert is_authed(a), "signup did not authenticate"
    return a


AUDIT = None
check("signup + auto-login", t_signup_login)


def t_login_existing() -> None:
    global AUDIT
    a = fresh()
    [t for t in a.text_input if t.label == "Username"][0].set_value("audit_user").run(timeout=30)
    [t for t in a.text_input if t.label == "Password"][0].set_value("audit1234").run(timeout=30)
    btn(a, "Login").set_value(True).run(timeout=30)
    assert is_authed(a)
    AUDIT = a


check("login as existing user", t_login_existing)

# From here on: authenticated app
a = AUDIT if AUDIT is not None else authed()

# ============================ SIDEBAR =======================================
def t_sidebar_healthy() -> None:
    b = a
    btn(b, "Healthy").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["vitals"]["spo2"] == 98.0


check("sidebar: Healthy scenario", t_sidebar_healthy)


def t_sidebar_watchlist() -> None:
    b = a
    btn(b, "Watch-list").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["vitals"]["heart_rate"] == 104.0


check("sidebar: Watch-list scenario", t_sidebar_watchlist)


def t_sidebar_emergency() -> None:
    b = a
    btn(b, "Emergency").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["vitals"]["spo2"] == 87.0


check("sidebar: Emergency scenario", t_sidebar_emergency)

# ============================ VITALS SLIDERS ================================
def t_vitals_sliders() -> None:
    b = a
    sliders = [s for s in b.slider]
    assert len(sliders) == 6, f"expected 6 sliders, got {len(sliders)}"
    hr = [s for s in b.slider if "Heart rate" in (s.label or "")][0]
    hr.set_value(150).run(timeout=30)
    assert not b.exception
    assert b.session_state["vitals"]["heart_rate"] == 150
    hr.set_value(72).run(timeout=30)


check("vitals: all 6 sliders move and update verdict", t_vitals_sliders)

# ============================ MEDICATIONS ===================================
def t_med_add() -> None:
    b = a
    [t for t in b.text_input if t.label == "Medicine name"][0].set_value("Audit Pill 5mg").run(timeout=30)
    btn(b, "➕ Add").set_value(True).run(timeout=30)
    assert not b.exception
    names = [m["name"] for m in b.session_state["meds"]]
    assert "Audit Pill 5mg" in names


check("meds: Add button adds medicine", t_med_add)


def t_med_taken_skip() -> None:
    b = a
    today = date.today()
    taken = btn(b, "✅ Taken")
    taken.set_value(True).run(timeout=30)
    assert not b.exception
    first = b.session_state["meds"][0]
    assert today in first["taken"], "Taken not recorded"
    skip = btn(b, "❌ Skip")
    skip.set_value(True).run(timeout=30)
    assert not b.exception
    first = b.session_state["meds"][0]
    assert today in first["missed"]


check("meds: Taken and Skip buttons record status", t_med_taken_skip)

# ============================ AI DOCTOR CHAT ================================
def t_chat_quick_prompt() -> None:
    b = a
    btn(b, "Crushing chest pain").set_value(True).run(timeout=30)
    assert not b.exception
    msgs = b.session_state["chat"]
    assert msgs[-1]["level"] == "Critical", f"expected Critical, got {msgs[-1]}"


check("AI doctor: chest pain quick button -> Critical", t_chat_quick_prompt)


def t_chat_runny_nose() -> None:
    b = a
    btn(b, "Runny nose and cough").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["chat"][-1]["level"] == "Low"


check("AI doctor: runny nose quick button -> Low", t_chat_runny_nose)

# ============================ RECOVERY TRACKER ==============================
def t_recovery_example_1() -> None:
    b = a
    btn(b, "1️⃣").set_value(True).run(timeout=30)
    assert not b.exception
    rec = b.session_state["recovery"]
    assert rec and rec["disease"] == "Type 2 Diabetes"


check("recovery: example 1 loads (month-1 due)", t_recovery_example_1)


def t_recovery_example_4_recheck() -> None:
    b = a
    btn(b, "4️⃣").set_value(True).run(timeout=30)
    assert not b.exception
    rec = b.session_state["recovery"]
    months = [r["months"] for r in rec["plan"]]
    assert 9 in months, f"9-month re-check missing: {months}"


check("recovery: example 4 has 9-month re-check", t_recovery_example_4_recheck)


def t_recovery_example_5_cured() -> None:
    b = a
    btn(b, "5️⃣").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["recovery"]["status"] == "cured"


check("recovery: example 5 is cured", t_recovery_example_5_cured)


def t_recovery_time_travel() -> None:
    b = a
    btn(b, "+1 month").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["clock"] > date.today()
    btn(b, "Reset to today").set_value(True).run(timeout=30)
    assert b.session_state["clock"] == date.today()


check("recovery: time-travel + reset buttons", t_recovery_time_travel)


def t_recovery_reset_case() -> None:
    b = a
    btn(b, "Discharge & start").set_value(True).run(timeout=30)
    assert not b.exception
    assert b.session_state["recovery"] is None
    # restore a case for later checks
    btn(b, "2️⃣").set_value(True).run(timeout=30)
    assert b.session_state["recovery"] is not None


check("recovery: discharge + load example 2", t_recovery_reset_case)

# ============================ REPORT TRANSLATOR =============================
def t_report_sample_button() -> None:
    b = a
    btn(b, "Load sample").set_value(True).run(timeout=30)
    assert not b.exception
    rep = b.session_state["report"]
    assert rep and len(rep["results"]) == 12, len(rep["results"]) if rep else 0


check("report: Load sample button decodes 12 markers", t_report_sample_button)


def t_report_paste_decode() -> None:
    b = a
    area = [t for t in b.text_area if "paste" in (t.label or "").lower()][0]
    area.set_value("Hemoglobin 9.1 g/dL\nFasting Glucose 142 mg/dL\nTSH 7.2 uIU/mL").run(timeout=30)
    btn(b, "Decode pasted text").set_value(True).run(timeout=30)
    assert not b.exception
    rep = b.session_state["report"]
    statuses = {r.analyte: r.status for r in rep["results"]}
    assert statuses.get("Hemoglobin") == "Low"
    assert statuses.get("Glucose") == "High"
    assert statuses.get("TSH") == "High"


check("report: paste text -> decode works", t_report_paste_decode)

def t_chat_free_text() -> None:
    b = a
    ci = [c for c in b.chat_input]
    assert ci, "chat_input not found"
    ci[0].set_value("I have a mild fever since yesterday").run(timeout=30)
    assert not b.exception
    assert b.session_state["chat"][-1]["level"] == "Moderate"


check("AI doctor: free-text input -> Moderate for fever", t_chat_free_text)


def t_med_multiselect_times() -> None:
    b = a
    ms = [m for m in b.multiselect if "Times per day" in (m.label or "")]
    assert ms, "times multiselect not found"
    ms[0].set_value(["08:00", "14:30", "22:00"]).run(timeout=30)
    assert not b.exception
    btn(b, "➕ Add").set_value(True).run(timeout=30)
    assert not b.exception
    added = [m for m in b.session_state["meds"] if m["name"] == "Audit Pill 5mg"]
    assert added and added[-1]["times"] == ["08:00", "14:30", "22:00"], added[-1]["times"] if added else "not added"


check("meds: time multiselect adds 3 custom times", t_med_multiselect_times)

# ============================ LOGOUT ========================================
def t_logout() -> None:
    b = a
    btn(b, "Logout").set_value(True).run(timeout=30)
    assert not b.exception
    assert not is_authed(b)
    assert b.query_params.get("google") != "1"


check("sidebar: Logout returns to auth page", t_logout)

# ============================ SUMMARY =======================================
print("\n" + "=" * 60)
passed = sum(1 for _, r in RESULTS if r == "PASS")
failed = len(RESULTS) - passed
print(f"AUDIT COMPLETE: {passed} passed, {failed} failed / {len(RESULTS)}")
for name, res in RESULTS:
    if res != "PASS":
        print("  FAILED:", name, "->", res)
raise SystemExit(1 if failed else 0)
