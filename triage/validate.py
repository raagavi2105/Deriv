#!/usr/bin/env python3
"""
Pipeline Validation Script
Validates all artifacts for completeness, schema correctness, and business-rule compliance.

Usage:
    python validate.py
"""
import json
import sys
from pathlib import Path
from typing import Any, List

sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.schemas import (
    Category,
    ComplianceViolation,
    CorrectionAction,
    RiskLevel,
)

PASS = "✓"
FAIL = "✗"
WARN = "⚠"

errors:   List[str] = []
warnings: List[str] = []


def check(condition: bool, message: str, warn: bool = False) -> bool:
    tag = PASS if condition else (WARN if warn else FAIL)
    print(f"  {tag} {message}")
    if not condition:
        (warnings if warn else errors).append(message)
    return condition


def load_json(path: Path) -> Any:
    if not check(path.exists(), f"File exists: {path.name}"):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        check(True, f"Valid JSON: {path.name}")
        return data
    except json.JSONDecodeError as exc:
        check(False, f"Valid JSON: {path.name} — {exc}")
        return None


# ── Stage validators ──────────────────────────────────────────────────────────

def validate_classifications(messages: List, data: List) -> None:
    print("\n[Stage 1] Initial Classifications")
    msg_ids = {m["id"] for m in messages}
    cls_ids = {d["id"] for d in data} if data else set()
    check(msg_ids == cls_ids, f"All {len(msg_ids)} messages classified")

    valid_cats = {c.value for c in Category}
    for item in (data or []):
        mid  = item.get("id")
        cat  = item.get("category")
        conf = item.get("confidence", -1)
        rev  = item.get("needs_human_review")

        check(cat in valid_cats, f"  ID {mid}: valid category '{cat}'")
        check(0.0 <= conf <= 1.0, f"  ID {mid}: confidence in [0,1] ({conf})")
        if conf < 0.7:
            check(rev is True,  f"  ID {mid}: needs_human_review=True when confidence={conf:.2f}")
        else:
            check(rev is False, f"  ID {mid}: needs_human_review=False when confidence={conf:.2f}")


def validate_risk_scores(classifications: List, data: List) -> None:
    print("\n[Stage 2] Risk Scores")
    if not data:
        check(False, "Risk scores present")
        return

    msg_ids  = {d["id"] for d in classifications}
    risk_ids = {d["id"] for d in data}
    check(msg_ids == risk_ids, f"All {len(msg_ids)} messages have risk scores")

    valid_levels = {r.value for r in RiskLevel}
    for item in data:
        mid   = item.get("id")
        level = item.get("risk_level")
        check(level in valid_levels, f"  ID {mid}: valid risk_level '{level}'")


def validate_drafts(messages: List, risk_scores: List, data: List) -> None:
    print("\n[Stage 3] Draft Responses")
    if not data:
        check(False, "Draft responses present")
        return

    msg_ids   = {m["id"] for m in messages}
    draft_ids = {d["id"] for d in data}
    check(msg_ids == draft_ids, f"All {len(msg_ids)} messages have drafts")

    risk_map = {r["id"]: r["risk_level"] for r in (risk_scores or [])}
    for item in data:
        mid   = item.get("id")
        mode  = item.get("drafting_mode")
        risk  = risk_map.get(mid, "medium")
        resp  = item.get("draft_response", "")

        if risk in ("high", "critical"):
            check(mode == "individual", f"  ID {mid}: high/critical → individual drafting (got: {mode})")
        else:
            check(mode == "batched",    f"  ID {mid}: low/medium → batched drafting (got: {mode})")

        check(len(resp) > 10, f"  ID {mid}: draft response has content")


def validate_compliance(data: List) -> None:
    print("\n[Stage 4] Compliance Results")
    if not data:
        check(False, "Compliance data present")
        return

    valid_violations = {v.value for v in ComplianceViolation}
    for item in data:
        mid = item.get("id")
        for v in item.get("violations", []):
            check(v in valid_violations, f"  ID {mid}: valid violation '{v}'")


def validate_corrections() -> List:
    print("\n[Stage 5] Corrections (corrections.jsonl)")
    if not check(config.CORRECTIONS_FILE.exists(), "corrections.jsonl exists", warn=True):
        return []

    valid_actions = {a.value for a in CorrectionAction}
    corrections = []
    with open(config.CORRECTIONS_FILE) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                check(item.get("action") in valid_actions, f"  Line {i}: valid action '{item.get('action')}'")
                check("timestamp" in item, f"  Line {i}: has timestamp")
                corrections.append(item)
            except json.JSONDecodeError:
                check(False, f"  Line {i}: valid JSON")

    check(len(corrections) > 0, "Has at least one correction entry", warn=True)
    return corrections


def validate_reclassification(messages: List, data: List, corrections: List) -> None:
    print("\n[Stage 6] Reclassification")
    if not data:
        check(False, "Reclassification data present")
        return

    msg_ids     = {m["id"] for m in messages}
    reclass_ids = {d["id"] for d in data}
    check(msg_ids == reclass_ids, f"All {len(msg_ids)} messages reclassified")

    for item in data:
        mid = item.get("id")
        check("confidence_before" in item and "confidence_after" in item,
              f"  ID {mid}: has before/after confidence")
        check("improved" in item, f"  ID {mid}: has 'improved' flag")


def validate_analytics(data: Any) -> None:
    print("\n[Stage 7] Analytics")
    if not data:
        check(False, "Analytics data present")
        return
    for key in ("accuracy_delta", "category_distribution", "compliance_failure_count",
                "risk_distribution", "human_review_count"):
        check(key in data, f"  analytics_summary has '{key}'")


def validate_routing(messages: List, data: List) -> None:
    print("\n[Stage 8] Routing Decisions")
    if not data:
        check(False, "Routing decisions present")
        return
    msg_ids    = {m["id"] for m in messages}
    routing_ids = {d["id"] for d in data}
    check(msg_ids == routing_ids, f"All {len(msg_ids)} messages have routing decisions")
    for item in data:
        mid = item.get("id")
        check("team" in item and "sla" in item, f"  ID {mid}: has team and SLA")


def validate_llm_logs(logs: List) -> None:
    print("\n[Stage 9] LLM Observability Logs")
    check(len(logs) > 0, "llm_calls.jsonl has entries")

    required_stages = {"classification", "risk_scoring", "drafting", "compliance_check", "reclassification"}
    found_stages    = {d.get("stage") for d in logs}
    for stage in required_stages:
        check(stage in found_stages, f"  Has log entry for stage: {stage}")

    reclass_logs = [d for d in logs if d.get("stage") == "reclassification"]
    if reclass_logs:
        # Warn only — few_shot is False when no operator corrections exist yet
        check(
            any(d.get("few_shot_examples_included") for d in reclass_logs),
            "  Reclassification log: few_shot_examples_included=True",
            warn=True,
        )

    for i, item in enumerate(logs):
        check(bool(item.get("prompt_hash")), f"  Log {i+1}: has prompt_hash")
        check(bool(item.get("timestamp")),   f"  Log {i+1}: has timestamp")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("PIPELINE VALIDATION")
    print("=" * 60)

    messages_data = load_json(config.SUPPORT_MESSAGES_PATH)
    if not messages_data:
        print(f"\n{FAIL} Cannot validate without support_messages.json")
        sys.exit(1)

    print("\n[Artifacts] File existence check")
    required_paths = [
        config.INITIAL_CLASSIFICATIONS_PATH,
        config.RISK_SCORES_PATH,
        config.DRAFT_RESPONSES_PATH,
        config.RESPONSE_COMPLIANCE_PATH,
        config.RECLASSIFIED_OUTPUTS_PATH,
        config.TRIAGE_OUTPUT_PATH,
        config.ANALYTICS_SUMMARY_PATH,
        config.ROUTING_DECISIONS_PATH,
        config.LLM_LOG_FILE,
    ]
    for p in required_paths:
        check(p.exists(), p.name)

    # Load all artifacts
    classifications   = load_json(config.INITIAL_CLASSIFICATIONS_PATH) or []
    risk_scores       = load_json(config.RISK_SCORES_PATH)             or []
    drafts            = load_json(config.DRAFT_RESPONSES_PATH)         or []
    compliance_data   = load_json(config.RESPONSE_COMPLIANCE_PATH)     or []
    reclassifications = load_json(config.RECLASSIFIED_OUTPUTS_PATH)    or []
    analytics         = load_json(config.ANALYTICS_SUMMARY_PATH)
    routing           = load_json(config.ROUTING_DECISIONS_PATH)       or []

    llm_logs = []
    if config.LLM_LOG_FILE.exists():
        with open(config.LLM_LOG_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        llm_logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    validate_classifications(messages_data, classifications)
    validate_risk_scores(classifications, risk_scores)
    validate_drafts(messages_data, risk_scores, drafts)
    validate_compliance(compliance_data)
    corrections = validate_corrections()
    validate_reclassification(messages_data, reclassifications, corrections)
    validate_analytics(analytics)
    validate_routing(messages_data, routing)
    validate_llm_logs(llm_logs)

    print("\n" + "=" * 60)
    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        for e in errors:
            print(f"  {FAIL} {e}")
        sys.exit(1)
    elif warnings:
        print(f"VALIDATION PASSED WITH WARNINGS — {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  {WARN} {w}")
    else:
        print("VALIDATION PASSED — All checks passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()