# 🩺 AI Health Assistance

**Decodes medical jargon • Triages symptoms • Visualises vital health metrics — in real time.**

> Patients don't die from lack of information — they die from information they can't understand and can't act on. AI Health Assistance turns panic into a plan.

> ⚕️ **Educational prototype — not a medical device.** In an emergency, always contact local emergency services.

---

## 📁 Submission Kit (Tech Expo)

| Module | File | What's inside |
|---|---|---|
| 1. Championship Pitch | [`docs/01_pitch_and_story.md`](docs/01_pitch_and_story.md) | Problem/solution, "Why We Win", 2-minute judge script |
| 2. Dashboard UI Blueprint | [`docs/02_dashboard_ui_blueprint.md`](docs/02_dashboard_ui_blueprint.md) | Layout architecture, vitals cards, translator widget, triage gauge |
| 3. Runnable Prototype | [`prototype/`](prototype/) | **Live Streamlit + Plotly dashboard** (below) |
| 4. Architecture & Stack | [`docs/03_architecture_and_stack.md`](docs/03_architecture_and_stack.md) | ASCII data-flow diagram, full tech stack, HIPAA controls |
| 5. Judge Defense Matrix | [`docs/04_judge_defense_matrix.md`](docs/04_judge_defense_matrix.md) | 5 hardest questions + confident answers |

## 🚀 Run the Live Prototype (Module 3)

Requires Python 3.11+.

```bash
cd prototype
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Then open the printed local URL (usually `http://localhost:8501`).

**The 45-second demo path:**
1. **Vitals tab** — all green. Click **"🎬 Scenario: Emergency"** in the sidebar → watch the gauge slam to 🔴 Critical 100/100.
2. **Report Translator tab** — paste the sample lab text → plain-English split view.
3. **Symptom Chat tab** — try *"crushing chest pain"* (🔴) vs *"runny nose and cough"* (🟢).

## 🧪 Tests

```bash
cd prototype
.venv\Scripts\python -m pytest test_core.py -q     # 8 tests — triage + translator logic
```

## 📱 Mobile App (this repo)

The repo also hosts the **React Native (Expo SDK 57)** front-end that mirrors this design system on mobile:

```bash
npm install
npm start        # scan QR with the Expo Go app, or press w for web
```

## 🗺️ Roadmap

- [x] Deterministic triage engine with red-flag override
- [x] Lab report translator (PDF/text → plain English)
- [x] Symptom triage chat with risk-level tags
- [ ] Wearable API ingestion (HealthKit / Health Connect)
- [ ] Fine-tuned medical LLM translation layer (Med42/OpenBioLLM)
- [ ] Clinician review mode + hospital pilot
