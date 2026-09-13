# Module 4 — System Architecture & Tech Stack

## 1. ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (per user)                              │
│                                                                             │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐                │
│   │ Wearable API │   │ Manual input │   │ Lab report PDF / │                │
│   │ (Fitbit/Apple│   │ (sliders/    │   │ text upload      │
│   │  Health/Garmin│  │  chat)       │   │                  │                │
│   └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘                │
└──────────┼──────────────────┼─────────────────────┼─────────────────────────┘
           │  REST/SDK (heart rate, SpO2, BP, sleep, temp)
           ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. PRE-PROCESSING LAYER                                                    │
│     • Unit normalisation  (°F↔°C, kg/mg-dL variants)                        │
│     • Noise filtering     (rolling median over 5-sample window)             │
│     • Deduplication       (drop double-sent readings)                       │
│     • OCR/PDF extraction  (pypdf → text)                                    │
│     • PHI tokenisation    (names/IDs → vault tokens; raw PII never          │
│                            reaches model context)                           │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │  clean vitals + extracted text
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. AI / LAYER                                                              │
│                                                                             │
│   ┌────────────────────────────┐    ┌────────────────────────────────────┐  │
│   │ 2a. RULE-BASED TRIAGE      │    │ 2b. FINE-TUNED MEDICAL LLM         │  │
│   │     ENGINE  (always-on)    │    │  (translation & explanation only)  │  │
│   │                            │    │                                    │  │
│   │ • Clinical reference bands │    │ • Base: Med42 / OpenBioLLM (70B)   │  │
│   │ • Flat-points composite    │    │   OR GPT-4o-medical class via API  │  │
│   │   score 0–100              │    │ • Fine-tune: 40k (lab-report,      │  │
│   │ • RED-FLAG OVERRIDE: any   │    │   plain-English) pairs; LoRA       │  │
│   │   urgent vital floors      │    │   adapters per specialty           │  │
│   │   score at 70 → CRITICAL   │    │ • Output: per-marker "why it       │  │
│   │ • Runs 100% locally —      │    │   matters" + next-step phrasing    │  │
│   │   zero net dependency      │    │ • Hallucination guards: grounded   │  │
│   └────────────┬───────────────┘    │   only on extracted values; every  │  │
│                │                    │   claim cites the source line      │  │
│                └─────────┬──────────┴────────────────────────────────────┘  │
│                          ▼                                                  │
│   ┌────────────────────────────────────────────┐                            │
│   │ 2c. SYMPTOM INTENT ROUTER                  │                            │
│   │  • Red-flag keyword match (safety first)   │                            │
│   │  • Fallback: duration/severity heuristics  │                            │
│   │  • Escalates vague → human-in-the-loop     │                            │
│   └────────────┬───────────────────────────────┘                            │
└───────────────┼─────────────────────────────────────────────────────────────┘
                │  {level, score, flags[], steps[], explanations[]}
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. TRIAGE ENGINE (decision layer)                                          │
│     • Composite 0–100 score  →  LOW / MODERATE / CRITICAL                   │
│     • Action mapping: self-care  |  doctor 24–48h  |  emergency now         │
│     • Explainability log: every verdict records which bands fired           │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │  verdict + explanation payload
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. DASHBOARD UI  (Streamlit prototype / React Native production)           │
│                                                                             │
│   ┌─────────────┐  ┌──────────────────┐  ┌────────────┐  ┌───────────────┐  │
│   │ Verdict     │  │ Vitals cards     │  │ Triage     │  │ Report        │  │
│   │ banner      │  │ (green/amber/red)│  │ gauge      │  │ translator    │  │
│   └─────────────┘  └──────────────────┘  └────────────┘  └───────────────┘  │
│                 chat interface  ·  wearable sliders  ·  trend charts        │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ (optional sync)
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. SECURITY & COMPLIANCE WRAPPER (cross-cutting, all layers)               │
│   • TLS 1.3 in transit · AES-256 at rest · per-user envelope encryption     │
│   • RBAC: user < clinician < admin · immutable audit log of every verdict   │
│   • HIPAA: BAAs with all vendors, PHI minimisation, 30-day retention        │
│   • Data residency pinning (region-of-user storage) · no PHI in prompts     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data flow in one line:** Wearable/PDF/chat → normalise + de-identify → (rules ∥ LLM) → explainable triage verdict → color-coded dashboard → audited action.

## 2. Technology Stack (detailed)

### Frontend
| Layer | Prototype (this repo) | Production target |
|---|---|---|
| Dashboard | **Streamlit 1.63** | **React Native (Expo SDK 57)** — same design tokens |
| Charts | **Plotly 7** indicators/scatter | `react-native-svg` + Victory Native |
| Routing/tabs | Streamlit tabs | **Expo Router** (file-based) |
| State | `st.session_state` | Zustand + React Query |

### Backend
| Concern | Choice | Why |
|---|---|---|
| API framework | FastAPI (Python 3.12) | Async websockets fit wearable streams; Pydantic schemas double as validation |
| Realtime ingest | WebSocket + Redis Streams | Wearable bursts; backpressure-safe |
| Persistence | PostgreSQL 16 + TimescaleDB | Relational + hypertables for vitals time-series |
| Jobs | Celery workers | Report OCR/translation off the request path |

### AI / LLM
| Component | Choice | Rationale |
|---|---|---|
| Triage core | Deterministic rules (this prototype) | Auditable, offline-safe, red-flag guarantees — regulators' favorite property |
| Report translation | **Med42-70B / OpenBioLLM fine-tuned (LoRA)** on 40k report-summary pairs; falls back to GPT-4o class API | Clinical grounding + cost control |
| Guardrails | Output schema validation; answers restricted to extracted values; refusal template for diagnosis requests | Hallucination containment |
| On-device fallback | Quantised Phi-3-mini class model | Low-connectivity regions |

### Security & HIPAA compliance
| Control | Implementation |
|---|---|
| Transport | TLS 1.3 everywhere; certificate pinning in mobile apps |
| At rest | AES-256, per-user envelope keys (AWS KMS / cloud HSM) |
| PHI minimisation | Tokenised names/IDs before any model call; raw PHI never enters prompts |
| Access control | RBAC + JWT short-lived tokens; clinician review is opt-in consented |
| Audit | Immutable, timestamped log of every verdict & data access (HIPAA §164.312(b)) |
| Vendors | BAAs signed (cloud, LLM provider); subprocessor register maintained |
| Retention | 30-day rolling raw vitals; summaries user-deletable ("right to erase") |
| Residency | Region-pinned storage (e.g., India data stays in `ap-south-1`) |
| Disclaimer | Educational/triage aid — *not* a medical device; emergency escalation always human-first |

### DevOps / quality
- CI: GitHub Actions → pytest (core logic, 8 tests) → AppTest smoke (app boots, scenario clicks) → build.
- Observability: OpenTelemetry traces per triage decision; verdict-score histograms as product health metrics.
- The Expo app in this repo is the mobile front-end target; the Streamlit prototype is the live demo vehicle for the Expo-judge circuit.
