import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

app = FastAPI(title="Fintech Triage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load(path: Path):
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _load_jsonl(path: Path):
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(ln) for ln in f if ln.strip()]


@app.get("/api/health")
def health():
    return {"status": "ok", "model": config.MODEL, "provider": "Groq"}


@app.get("/api/analytics")
def analytics():
    return _load(config.ANALYTICS_SUMMARY_PATH)


@app.get("/api/messages")
def messages():
    return _load(config.SUPPORT_MESSAGES_PATH)


@app.get("/api/classifications")
def classifications():
    return _load(config.INITIAL_CLASSIFICATIONS_PATH)


@app.get("/api/risk-scores")
def risk_scores():
    return _load(config.RISK_SCORES_PATH)


@app.get("/api/drafts")
def drafts():
    return _load(config.DRAFT_RESPONSES_PATH)


@app.get("/api/compliance")
def compliance():
    return _load(config.RESPONSE_COMPLIANCE_PATH)


@app.get("/api/reclassifications")
def reclassifications():
    return _load(config.RECLASSIFIED_OUTPUTS_PATH)


@app.get("/api/routing")
def routing():
    return _load(config.ROUTING_DECISIONS_PATH)


@app.get("/api/triage")
def triage():
    return _load(config.TRIAGE_OUTPUT_PATH)


@app.get("/api/logs")
def logs():
    return _load_jsonl(config.LLM_LOG_FILE)


@app.get("/api/corrections")
def corrections():
    return _load_jsonl(config.CORRECTIONS_FILE)
