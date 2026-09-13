# Module 2 — Dashboard UI Blueprint (Ultra-Intuitive Design)

> Design philosophy: **"Glance, understand, act."** A worried user scans the dashboard in under 5 seconds and leaves knowing exactly one thing: *what to do next.*

## 1. Layout Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER:  🩺 AI Health Assistance          [Live ●]  [profile]       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  LIVE TRIAGE VERDICT BANNER  (full-width, color = risk)        │  │
│  │  🟢 LOW RISK — Score 7/100 · "All core vitals look stable"     │  │
│  │  🟡 MODERATE — Score 40/100 · "Book a doctor within 24–48h"    │  │
│  │  🔴 CRITICAL — Score 100/100 · "Seek emergency care now"       │  │
│  └────────────────────────────────────────────────────────────────┘  │
├───────────────────────────────────────┬──────────────────────────────┤
│  LEFT (60%): VITALS PANEL             │  RIGHT (40%):                │
│  ┌──────────────┬──────────────┐      │  ┌────────────────────────┐  │
│  │ ❤️ Heart Rate │ 🫁 SpO₂      │      │  │ SMART TRIAGE GAUGE     │  │
│  │ 72 bpm  🟢   │ 98%  🟢      │      │  │  (0–100 semicircle,    │  │
│  ├──────────────┼──────────────┤      │  │   green→amber→red)     │  │
│  │ 🩸 BP        │ 🌡️ Temp      │      │  └────────────────────────┘  │
│  │ 118/76 🟢    │ 98.6°F 🟢    │      │  ┌────────────────────────┐  │
│  ├──────────────┼──────────────┤      │  │ ✅ RECOMMENDED STEPS   │  │
│  │ 😴 Sleep     │              │      │  │ (checklist, changes    │  │
│  │ 7.5 hrs 🟢   │              │      │  │  with risk level)      │  │
│  └──────────────┴──────────────┘      │  └────────────────────────┘  │
│  [🎛️ wearable sliders]                │  "Why this verdict" list     │
│  [📈 24h trend chart]                 │  (each flag → its band)      │
├───────────────────────────────────────┴──────────────────────────────┤
│  TABS: [📡 Vitals] [📄 Report Translator] [💬 Symptom Chat]          │
└──────────────────────────────────────────────────────────────────────┘
```

**Layout rules that make it "ultra-intuitive":**
1. **One verdict, top of page, biggest element** — a panicking user reads exactly one sentence.
2. **F-pattern scan**: cards read left→right in descending urgency weight (SpO₂ & BP get the widest cards on mobile).
3. **Color is the interface**: green/amber/red appear on *every* element — card borders, gauge zones, chat tags, steps list. No color-free state exists.
4. **Nothing enters the dashboard without a unit, a status, and a reason.** Three lines per card: *label → value → plain-English why.*

## 2. Vitals Panel — Dynamic Color-Coded Status Cards

| Vital | Healthy (🟢 `#16a34a`) | Caution (🟡 `#f59e0b`) | Urgent (🔴 `#dc2626`) |
|---|---|---|---|
| **Heart Rate** | 50–100 bpm | 40–50 or 100–135 | <40 or >135 |
| **SpO₂** | 92–100% | 88–92% | <88% |
| **BP Systolic** | 90–130 mmHg | 80–90 or 130–180 | <80 or >180 |
| **BP Diastolic** | 60–85 mmHg | 50–60 or 85–120 | <50 or >120 |
| **Temperature** | 97–99.5 °F | 94–97 or 99.5–104 | <94 or >104 °F |
| **Sleep** | 6–10 hrs | 4–6 or 10–12 | <4 or >12 hrs |

**Card anatomy** (one card, three states — same layout, different color):
```
┌─────────────────────────┐   border-top: 4px solid [status color]
│ 🟢 Heart Rate           │   label + status dot
│ 72 bpm                  │   2rem bold value in status color
│ "within normal range"   │   plain-English reason (always present)
└─────────────────────────┘
```
- Transitions animate color + value (CSS `transition: 300ms`) so a live wearable stream visibly "breathes."
- A card in Urgent state gets a subtle pulsing border — draws the eye without an alarm sound.
- Long-press / hover a card → sparkline of that vital's last 24h.

## 3. Medical Report Translator Widget (Split-Screen)

```
┌───────────────────────────────┬─────────────────────────────────────┐
│  🧾 COMPLEX MEDICAL INPUT     │  💬 PLAIN-ENGLISH SUMMARY           │
│  (what the lab sends)         │  (what the patient reads)           │
├───────────────────────────────┼─────────────────────────────────────┤
│  LABORATORY INVESTIGATION     │  ┌─────────────────────────────────┐│
│  REPORT                       │  │ Hemoglobin: 10.2 g/dL     [LOW] ││
│  Patient ID: 44291            │  │ ref: 13–17 g/dL                 ││
│  HEMATOLOGY                   │  │ 💬 Carries oxygen through your  ││
│  Hemoglobin      10.2 g/dL    │  │ blood — low levels cause        ││
│    (13.0 - 17.0)              │  │ tiredness and weakness.         ││
│  WBC Count       11,800 /µL   │  └─────────────────────────────────┘│
│    (4,000 - 11,000)           │  ┌─────────────────────────────────┐│
│  Platelets      250,000 /µL   │  │ WBC: 11,800/µL           [HIGH] ││
│    (150k - 410k)              │  │ 💬 Your infection-fighting      ││
│  BIOCHEMISTRY                 │  │ cells — high suggests your body ││
│  Glucose (F)     128 mg/dL    │  │ is fighting something.          ││
│    (70 - 99)                  │  └─────────────────────────────────┘│
│  HbA1c            6.1 %       │  ┌─────────────────────────────────┐│
│  TSH              6.1 µIU/mL  │  │ ⚠️ 3 of 5 markers outside range ││
│                               │  │ 📅 Bring this summary to your   ││
│  [UPLOAD PDF]  [PASTE TEXT]   │  │ doctor within a few days.       ││
└───────────────────────────────┴─────────────────────────────────────┘
```

**Design details:**
- Left panel is *intentionally intimidating* — the contrast IS the demo. Same data, two audiences.
- Each marker row: **name · value · color status pill · reference range · one-sentence "why it matters."**
- Status pills: `Normal` green / `High` red / `Low` amber — consistent with vitals colors.
- Footer banner only appears if ≥1 abnormal: severity-sorted, with a calendar-cue next step (never a diagnosis).
- Mobile: split view stacks vertically with a "Translate ▼" affordance.

## 4. Smart Symptom Triage Gauge (Interactive Risk Meter)

```
        SMART SYMPTOM TRIAGE
        ─────────────────────────────────
             ╭───────────╮
            ╱ ████░░░░░░ ╲
           │ ████  ▲ 42   │      0–34   🟢 LOW      → "Self-care + monitor"
           │░░░░░░░░░░░░░░│      35–64  🟡 MODERATE → "Doctor within 24–48h"
            ╲░░░░░░░░░░░░╱       65–100 🔴 CRITICAL → "Emergency care NOW"
             ╰───────────╯
        [ chat input: "Describe your symptoms…" ]
```

- **Gauge = the chat's pulse.** Every message re-animates the needle with the matched risk level; the zone colors are the same three greens/ambers/reds as everywhere else.
- Each bot reply carries a **risk tag** (pill in the corner): users see *why* the level changed — the matched red-flag keyword is quoted back.
- Recommended next steps render as a checklist that rewrites itself per level:
  - 🟢 Low → rest/hydrate/monitor + "escalate if X" criteria (always included)
  - 🟡 Moderate → doctor in 24–48h + what to track meanwhile
  - 🔴 Critical → emergency call as the literal first line, bolded, no other actions above it
- **Safety interaction pattern:** when a Critical verdict fires, the chat input dims and a persistent red banner pins to the top — the UI actively discourages "chatting through" an emergency.

## 5. Design System Snapshot

| Token | Value | Use |
|---|---|---|
| Green `#16a34a` | Healthy / Low | Card borders, gauge zone, pills |
| Amber `#f59e0b` | Caution / Moderate | Same surfaces |
| Red `#dc2626` | Urgent / Critical | Same surfaces |
| Font | System UI stack (SF/Segoe/Roboto) | Native feel, zero load time |
| Card radius | 14–16px | Soft, clinical-but-friendly |
| Verdict banner | Full-width, white-on-color | The single loudest element |
| Motion | 300ms ease transitions | Live-feel without distraction |

> Every rule above is implemented in `prototype/app.py` — the blueprint and the code are the same system, not two documents.
