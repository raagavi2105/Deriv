# Deriv — Fintech AI Support Triage Platform

A production-style, multi-stage AI orchestration pipeline for fintech customer support triage. Built with **Meta Llama 3.1 8B Instant** via **Groq API**, **FastAPI** backend, and a live analytics dashboard.

Live Deployed Link: https://deriv-omega.vercel.app/
---

## What It Does

Automatically processes customer support messages through a 14-stage AI pipeline:

1. **Classifies** messages into controlled categories
2. **Risk-scores** each case (low → critical)
3. **Drafts** compliant support responses
4. **Validates** responses for compliance violations
5. **Collects** operator corrections via CLI
6. **Reclassifies** with few-shot learning from corrections
7. **Measures** accuracy improvement before vs after
8. **Routes** cases to the right team with SLA enforcement
9. **Logs** every LLM call for full auditability

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI Model | Meta Llama 3.1 8B Instant |
| AI Provider | Groq API |
| Backend API | FastAPI + Uvicorn |
| Frontend | HTML / Tailwind CSS / Chart.js |
| Schema Validation | Pydantic v2 |
| CLI Interface | Rich |

---
## Application Screenshots

**Home Page**

![Home Page Dashboard](image/1.png)

**Escalation & Triage Result*

![JEscalation & Triage Result](image/2.png)

**Compilance Violations**

![Compilance Violations](image/3.png)

**LLM Log**

![LLM Log](image/4.png)

---

## Project Structure

```
Deriv/
├── triage/
│   ├── src/
│   │   ├── config.py              # Env config, routing matrix, artifact paths
│   │   ├── schemas.py             # Pydantic models + controlled vocabulary enums
│   │   ├── utils.py               # JSON extractor, retry-with-backoff decorator
│   │   ├── llm_logger.py          # Appends every LLM call to llm_calls.jsonl
│   │   ├── prompts/               # Modular prompt builder per stage
│   │   │   ├── classification.py
│   │   │   ├── risk_scoring.py
│   │   │   ├── response_drafting.py
│   │   │   └── compliance.py
│   │   └── stages/                # Isolated stage implementations
│   │       ├── s1_classification.py
│   │       ├── s2_risk_scoring.py
│   │       ├── s3_response_drafting.py
│   │       ├── s4_compliance_check.py
│   │       ├── s5_operator_corrections.py
│   │       ├── s6_reclassification.py
│   │       ├── s7_analytics.py
│   │       └── s8_routing.py
│   ├── backend/
│   │   └── main.py                # FastAPI REST API server
│   ├── frontend/
│   │   └── index.html             # Analytics dashboard (Chart.js)
│   ├── data/
│   │   └── support_messages.json  # Input: 20 fintech support messages
│   ├── run_pipeline.py            # Main orchestrator (state machine)
│   ├── validate.py                # Artifact validation script
│   ├── requirements.txt
│   └── .env.example
```

---

## Pipeline Stages

| # | Stage | Description |
|---|-------|-------------|
| 1 | `INPUTS_LOADED` | Load support messages from JSON |
| 2 | `PRIOR_CORRECTIONS_LOADED` | Read persisted operator corrections |
| 3 | `INITIAL_CLASSIFICATION_COMPLETE` | One batched LLM call classifies all messages |
| 4 | `RISK_SCORING_COMPLETE` | LLM for escalations; deterministic mapping for rest |
| 5 | `RESPONSES_DRAFTED` | Batched (low/medium) + individual calls (high/critical) |
| 6 | `COMPLIANCE_CHECK_COMPLETE` | LLM review + deterministic keyword scan |
| 7 | `OPERATOR_CORRECTIONS_COLLECTED` | Interactive Rich CLI correction interface |
| 8 | `FEW_SHOT_BLOCK_BUILT` | Build few-shot examples from corrections |
| 9 | `RECLASSIFICATION_COMPLETE` | Re-classify all messages with few-shot injection |
| 10 | `BEFORE_AFTER_COMPARISON_COMPLETE` | Compute accuracy delta |
| 11 | `ANALYTICS_GENERATED` | Full metrics and distribution summary |
| 12 | `ROUTING_DECISIONS` | Deterministic routing + escalation alerts |
| 13 | `VALIDATION_COMPLETE` | All artifacts validated |
| 14 | `RESULTS_FINALISED` | All outputs written |

---

## Controlled Vocabularies

**Categories:** `payments` · `technical` · `compliance` · `account` · `product_query` · `escalation`

**Risk Levels:** `low` · `medium` · `high` · `critical`

**Compliance Violations:** `promise` · `specific_timeline` · `liability_admission` · `non_compliant_financial_claim` · `none`

---

## Setup

```bash
cd triage

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

---

## Running

```bash
cd triage
source .venv/bin/activate

# Run full pipeline (interactive operator correction mode)
python run_pipeline.py

# Run in CI / headless mode (auto-accepts all corrections)
python run_pipeline.py --auto

# Validate all artifacts after a run
python validate.py
```

---

## Servers

```bash
# Backend API — port 8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend Dashboard — port 3000
cd frontend && python3 -m http.server 3000
```

| Link | URL |
|------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger API Docs | http://localhost:8000/docs |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/analytics` | Summary metrics + accuracy delta |
| GET | `/api/triage` | Full merged triage record per message |
| GET | `/api/classifications` | Initial classifications |
| GET | `/api/risk-scores` | Risk scores with triggering criteria |
| GET | `/api/drafts` | Draft support responses |
| GET | `/api/compliance` | Compliance violation results |
| GET | `/api/reclassifications` | Few-shot reclassification results |
| GET | `/api/routing` | Routing decisions + escalation alerts |
| GET | `/api/logs` | LLM observability log |

---

## Output Artifacts

```
triage/artifacts/
├── initial_classifications.json    # Stage 1
├── risk_scores.json                # Stage 2
├── draft_responses.json            # Stage 3
├── response_compliance.json        # Stage 4
├── reclassified_outputs.json       # Stage 6
├── triage_output.json              # Full merged output
├── analytics_summary.json          # Stage 7 metrics
├── routing_decisions.json          # Stage 8 routing
└── llm_calls.jsonl                 # One log line per LLM call

triage/corrections.jsonl            # Persists across runs
```

---

## Key Design Decisions

- **Separate LLM call per stage** — no collapsed prompts, every decision is independently auditable
- **Groq JSON mode** — `response_format={"type": "json_object"}` for reliable structured outputs
- **Deterministic fallbacks** — risk scoring and routing never block on LLM availability
- **Append-only corrections** — `corrections.jsonl` persists across runs and is never overwritten
- **Few-shot injection** — reclassification re-runs with operator corrections baked in as examples
- **Retry with exponential backoff** — all LLM calls retry up to 3× automatically
- **Keyword scan safety net** — compliance check catches violations even if the LLM misses them
