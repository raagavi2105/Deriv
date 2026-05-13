# Fintech AI Support Triage Platform

A production-style, multi-stage AI orchestration pipeline for fintech customer support triage.

**Model:** Meta Llama 3.1 8B Instant via Groq API  
**Language:** Python 3.11+

---

## Architecture

```
run_pipeline.py                   ← Main orchestrator (state machine)
│
├── Stage 1  s1_classification    ← Batched LLM call, classifies all messages
├── Stage 2  s2_risk_scoring      ← LLM for escalations; deterministic for rest
├── Stage 3  s3_response_drafting ← Batched (low/med) + individual (high/crit)
├── Stage 4  s4_compliance_check  ← LLM review + deterministic keyword scan
├── Stage 5  s5_operator_corrections ← Rich CLI correction interface
├── Stage 6  s6_reclassification  ← Few-shot reclassification from corrections
├── Stage 7  s7_analytics         ← Metrics and accuracy delta
└── Stage 8  s8_routing           ← Deterministic routing matrix + alerts

src/
├── config.py       ← Env-based configuration and artifact paths
├── schemas.py      ← Pydantic models and enums (controlled vocabularies)
├── llm_logger.py   ← Appends every LLM call to llm_calls.jsonl
├── utils.py        ← JSON extractor, retry decorator
├── prompts/        ← Modular prompt builders (one file per stage)
└── stages/         ← Isolated stage implementations
```

### Controlled Vocabularies

| Type | Values |
|------|--------|
| Categories | `payments` `technical` `compliance` `account` `product_query` `escalation` |
| Risk levels | `low` `medium` `high` `critical` |
| Compliance violations | `promise` `specific_timeline` `liability_admission` `non_compliant_financial_claim` `none` |
| Correction actions | `accepted` `corrected` `skipped` |

---

## Setup

```bash
cd triage
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file (or copy `.env.example`):

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL=llama-3.1-8b-instant
```

---

## Running

```bash
# Full pipeline with interactive operator corrections
python run_pipeline.py

# CI / headless mode (auto-accepts all corrections)
python run_pipeline.py --auto

# Validate all artifacts after a run
python validate.py
```

---

## Pipeline Stages

| Stage | State | Description |
|-------|-------|-------------|
| 0 | `INIT` | Environment validation |
| 1 | `INPUTS_LOADED` | Load `support_messages.json` |
| 2 | `PRIOR_CORRECTIONS_LOADED` | Read persisted corrections |
| 3 | `INITIAL_CLASSIFICATION_COMPLETE` | One batched LLM call |
| 4 | `RISK_SCORING_COMPLETE` | LLM for escalations, deterministic for rest |
| 5 | `RESPONSES_DRAFTED` | Batched + individual calls by risk tier |
| 6 | `COMPLIANCE_CHECK_COMPLETE` | LLM review + keyword scan |
| 7 | `OPERATOR_CORRECTIONS_COLLECTED` | Interactive CLI review |
| 8 | `FEW_SHOT_BLOCK_BUILT` | Build examples from corrections |
| 9 | `RECLASSIFICATION_COMPLETE` | Re-classify with few-shot injection |
| 10 | `BEFORE_AFTER_COMPARISON_COMPLETE` | Accuracy delta |
| 11 | `ANALYTICS_GENERATED` | Full metrics |
| 12 | `VALIDATION_COMPLETE` | `python validate.py` |
| 13 | `RESULTS_FINALISED` | All artifacts written |

---

## Output Artifacts

```
artifacts/
├── initial_classifications.json   ← Stage 1 output
├── risk_scores.json               ← Stage 2 output
├── draft_responses.json           ← Stage 3 output
├── response_compliance.json       ← Stage 4 output
├── reclassified_outputs.json      ← Stage 6 output
├── triage_output.json             ← Full merged record per message
├── analytics_summary.json         ← Stage 7 metrics
├── routing_decisions.json         ← Stage 8 routing + alerts
└── llm_calls.jsonl                ← Observability log (one line per LLM call)

corrections.jsonl                  ← Persists across runs (operator feedback)
```

---

## Key Design Decisions

- **Separate LLM calls per stage** — no collapsed prompts, full auditability
- **Groq JSON mode** — `response_format={"type": "json_object"}` for reliable structured output
- **Deterministic fallbacks** — risk scoring and routing never block on LLM availability
- **Corrections persist** — `corrections.jsonl` is append-only and never overwritten
- **Few-shot injection** — reclassification re-runs with operator corrections baked in
- **Retry with backoff** — all LLM calls retry 3× with exponential delay
- **Keyword scan as safety net** — compliance check catches obvious violations even if LLM misses them