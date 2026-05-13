import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
MODEL: str = os.getenv("MODEL", "llama-3.1-8b-instant")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

BASE_DIR = Path(__file__).parent.parent
ARTIFACTS_DIR = BASE_DIR / os.getenv("ARTIFACTS_DIR", "artifacts")
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
CORRECTIONS_FILE = BASE_DIR / os.getenv("CORRECTIONS_FILE", "corrections.jsonl")
LLM_LOG_FILE = ARTIFACTS_DIR / "llm_calls.jsonl"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

SUPPORT_MESSAGES_PATH       = DATA_DIR      / "support_messages.json"
INITIAL_CLASSIFICATIONS_PATH = ARTIFACTS_DIR / "initial_classifications.json"
RISK_SCORES_PATH            = ARTIFACTS_DIR / "risk_scores.json"
DRAFT_RESPONSES_PATH        = ARTIFACTS_DIR / "draft_responses.json"
RESPONSE_COMPLIANCE_PATH    = ARTIFACTS_DIR / "response_compliance.json"
RECLASSIFIED_OUTPUTS_PATH   = ARTIFACTS_DIR / "reclassified_outputs.json"
TRIAGE_OUTPUT_PATH          = ARTIFACTS_DIR / "triage_output.json"
ANALYTICS_SUMMARY_PATH      = ARTIFACTS_DIR / "analytics_summary.json"
ROUTING_DECISIONS_PATH      = ARTIFACTS_DIR / "routing_decisions.json"

ROUTING_MATRIX = {
    "payments":      {"team": "Payments Support",    "sla": "4 hours",  "escalation_path": "Finance Escalation Team"},
    "technical":     {"team": "Technical Support",   "sla": "8 hours",  "escalation_path": "Senior Technical Team"},
    "compliance":    {"team": "Compliance Team",     "sla": "2 hours",  "escalation_path": "Compliance Officer"},
    "account":       {"team": "Account Management",  "sla": "6 hours",  "escalation_path": "Account Supervisor"},
    "product_query": {"team": "Product Support",     "sla": "24 hours", "escalation_path": "Product Team"},
    "escalation":    {"team": "Escalations Team",    "sla": "1 hour",   "escalation_path": "Executive Escalation"},
}

DETERMINISTIC_RISK_MAP = {
    "product_query": "low",
    "technical":     "medium",
    "account":       "medium",
    "payments":      "medium",
    "compliance":    "high",
    "escalation":    "high",
}