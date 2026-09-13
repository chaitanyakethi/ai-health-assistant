# Module 5 — Judge Q&A Defense Matrix

> Format: the hardest likely question → the 30-second confident answer → the killer detail if pressed. Deliver answers calm, specific, and never defensive.

---

## Q1. "Your triage rules are simplistic. A real patient has 200 variables. How is a 6-vital checklist medicine?"

**Answer:**
"Exactly right — and that's why our architecture separates *safety* from *sophistication*. The rule engine you see handles the safety floor: it's deterministic, auditable, and structurally cannot undersell an emergency — any urgent vital floors the score at Critical. Production layers a fine-tuned medical LLM and richer feature extraction on top, but they can only *raise* a risk level, never lower the red-flag floor below what the rules set. In safety-critical systems, the simplest component carries the highest-stakes guarantee. That's a feature, not a shortcut."

**If pressed:** "Analogy: aircraft use checklists *and* sophisticated autopilot. The checklist handles the non-negotiables. We do the same — and our pytest suite proves each rule's behavior."

---

## Q2. "LLMs hallucinate. A hallucinated medical explanation could harm someone. How do you prevent that?"

**Answer:**
"Three structural guards. First, **grounding**: the translator is only allowed to explain values that were machine-extracted from the report — if it's not in our parsed data, the model cannot mention it; every explanation cites its source line. Second, **schema enforcement**: outputs are validated JSON — analyte, value, status, one-sentence 'why' — anything else is regenerated or refused. Third, **scope refusal**: the model is fine-tuned to decline diagnosis questions and route them to the triage engine or a human. And crucially, hallucination-prone components sit *outside* the safety path — emergency escalation is rule-based, not generative."

**If pressed:** "We eval the translator with exact-match against clinician-written gold summaries; we track factual-precision, not fluency. Wrong on a value → it's a P1 bug, not a UX issue."

---

## Q3. "If your app tells someone 'you're fine' and they have a heart attack, who's liable? Would you launch this?"

**Answer:**
"Liability is exactly why we designed the escalation path to be louder than the reassurance path. The product never says 'you are fine' — it says 'all core vitals look stable — here's how to keep it that way,' with explicit escalate-if criteria on every Low verdict, and a standing 'not a medical device' disclaimer with emergency guidance one tap away. Legally we launch as a *wellness and navigation* layer — like the symptom checkers already shipping from Ada or Babylon — with clinician-in-the-loop review in our clinical pilot before any regulated claims. The moment we make diagnostic claims, we pursue the regulatory pathway deliberately, not accidentally."

**If pressed:** "Every verdict is logged with its inputs — the audit trail protects users and us. And our 'Moderate' band is deliberately over-inclusive; we err toward sending people to doctors."

---

## Q4. "What happens offline — villages, disaster zones, no internet? Or: your LLM needs a datacenter."

**Answer:**
"That constraint shaped the architecture, not the marketing. The triage engine and symptom router are 100% local and deterministic — the demo you've seen runs with Wi-Fi off. For report translation offline we ship a quantised small model — a Phi-3-mini-class LLM on device — that handles the 12 most common analytes; the big LLM is an online *enhancement*, not a dependency. Vitals sync opportunistically when connectivity returns. Low-connectivity markets aren't an edge case for us — they're a design requirement, and honestly a moat."

**If pressed:** "Core value metrics — triage verdict, next steps, red-flag detection — never leave the device. Cloud adds polish, not safety."

---

## Q5. "What's the business model? Consumer health apps churn out — and why would hospitals trust a hackathon build?"

**Answer:**
"Two-sided, sequenced. Near-term B2C freemium: symptom triage and vitals dashboard free — report translation and family sharing are the subscription, priced like one lab test per year. The wedge that builds durable trust: **clinician mode** — patients export an auditable summary, doctors review and correct the triage, and those corrections fine-tune the model. That's the hospital on-ramp: we don't sell hospitals software first, we sell them *better-prepared patients*, then pilot the dashboard in chronic-care programs where readmission penalties make ROI obvious. The hackathon build proves the UX; the pilot proves the medicine; the corrections loop builds the moat."

**If pressed:** "Our data flywheel: every clinician correction is a labeled training example competitors can't buy. Accuracy compounds with deployment."

---

## Bonus rapid-fire (know these cold)

| Question | 15-second answer |
|---|---|
| Accuracy of the triage bands? | Standard clinical reference ranges (AHA/WHO), published in-app; bands are config, not code — updatable per population. |
| What about false reassurance? | Low verdicts always ship with escalate-if criteria; we measure 'Low → ER within 48h' as our zero-tolerance metric. |
| Data privacy? | PHI tokenised before any model call; TLS 1.3 + AES-256; BAAs signed; region-pinned storage. |
| Why not just use GPT directly? | Deterministic safety floor + grounded translation + audit trail; a raw LLM can't certify a red-flag floor. |
| Wearable integration effort? | HealthKit/Health Connect/Fitbit Web APIs — OAuth per user; prototype's sliders simulate that stream honestly. |
| Team gaps? | Clinical advisory is our first hire with pilot revenue — we'd rather earn it than fake it. |
