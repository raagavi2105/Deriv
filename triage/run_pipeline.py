#!/usr/bin/env python3
"""
Fintech AI Support Triage Platform
Multi-stage AI orchestration pipeline using Groq + Meta Llama 3.1 8B Instant.

Usage:
    python run_pipeline.py              # interactive operator corrections
    python run_pipeline.py --auto       # skip interactive review (CI mode)
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.schemas import (
    ComplianceViolation,
    PipelineStage,
    SupportMessage,
    TriageRecord,
)
from src.stages.s1_classification import classify_messages
from src.stages.s2_risk_scoring import score_risks
from src.stages.s3_response_drafting import draft_responses
from src.stages.s4_compliance_check import check_compliance
from src.stages.s5_operator_corrections import collect_corrections
from src.stages.s6_reclassification import build_few_shot_block, reclassify_with_fewshot
from src.stages.s7_analytics import generate_analytics
from src.stages.s8_routing import generate_routing

console = Console()


def _stage(stage: PipelineStage, note: str = "") -> None:
    console.print(f"[bold green]▶ {stage.value}[/bold green]  [dim]{note}[/dim]")


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        if isinstance(data, list):
            json.dump(
                [item.model_dump() if hasattr(item, "model_dump") else item for item in data],
                f, indent=2,
            )
        elif hasattr(data, "model_dump"):
            json.dump(data.model_dump(), f, indent=2)
        else:
            json.dump(data, f, indent=2)


def _load_messages() -> List[SupportMessage]:
    if not config.SUPPORT_MESSAGES_PATH.exists():
        console.print(f"[red]ERROR: {config.SUPPORT_MESSAGES_PATH} not found.[/red]")
        sys.exit(1)
    with open(config.SUPPORT_MESSAGES_PATH) as f:
        return [SupportMessage(**m) for m in json.load(f)]


def main(auto_accept: bool = False) -> None:
    console.print(Panel(
        "[bold cyan]FINTECH AI SUPPORT TRIAGE PLATFORM[/bold cyan]\n"
        f"Model: [yellow]{config.MODEL}[/yellow]  •  Provider: [yellow]Groq[/yellow]",
        box=box.DOUBLE,
    ))

    if not config.GROQ_API_KEY:
        console.print("[red]ERROR: GROQ_API_KEY not set. Add it to triage/.env[/red]")
        sys.exit(1)

    # ── INIT ────────────────────────────────────────────────────────────────
    _stage(PipelineStage.INIT, "Initializing pipeline…")

    # ── INPUTS_LOADED ────────────────────────────────────────────────────────
    messages = _load_messages()
    _stage(PipelineStage.INPUTS_LOADED, f"{len(messages)} messages loaded")

    # ── PRIOR_CORRECTIONS_LOADED ─────────────────────────────────────────────
    prior_count = 0
    if config.CORRECTIONS_FILE.exists():
        with open(config.CORRECTIONS_FILE) as f:
            prior_count = sum(1 for ln in f if ln.strip())
    _stage(PipelineStage.PRIOR_CORRECTIONS_LOADED, f"{prior_count} prior corrections found")

    # ── STAGE 1 — INITIAL CLASSIFICATION ────────────────────────────────────
    console.print("\n[yellow]Stage 1 — Initial Classification…[/yellow]")
    classifications = classify_messages(messages)
    _save(config.INITIAL_CLASSIFICATIONS_PATH, classifications)
    _stage(PipelineStage.INITIAL_CLASSIFICATION_COMPLETE, f"{len(classifications)} messages classified")

    # ── STAGE 2 — RISK SCORING ───────────────────────────────────────────────
    console.print("\n[yellow]Stage 2 — Risk Scoring…[/yellow]")
    risk_scores = score_risks(messages, classifications)
    _save(config.RISK_SCORES_PATH, risk_scores)
    _stage(PipelineStage.RISK_SCORING_COMPLETE, f"{len(risk_scores)} messages scored")

    # ── STAGE 3 — RESPONSE DRAFTING ──────────────────────────────────────────
    console.print("\n[yellow]Stage 3 — Response Drafting…[/yellow]")
    drafts = draft_responses(messages, risk_scores)
    _save(config.DRAFT_RESPONSES_PATH, drafts)
    _stage(PipelineStage.RESPONSES_DRAFTED, f"{len(drafts)} responses drafted")

    # ── STAGE 4 — COMPLIANCE CHECK ───────────────────────────────────────────
    console.print("\n[yellow]Stage 4 — Compliance Check…[/yellow]")
    compliance = check_compliance(messages, drafts)
    _save(config.RESPONSE_COMPLIANCE_PATH, compliance)
    failures = sum(1 for c in compliance if not c.passed)
    _stage(PipelineStage.COMPLIANCE_CHECK_COMPLETE, f"{failures} violation(s) found")

    # ── STAGE 5 — OPERATOR CORRECTIONS ───────────────────────────────────────
    console.print("\n[yellow]Stage 5 — Operator Corrections…[/yellow]")
    corrections = collect_corrections(messages, classifications, risk_scores, auto_accept=auto_accept)
    corrected_count = sum(1 for c in corrections if c.action.value == "corrected")
    _stage(PipelineStage.OPERATOR_CORRECTIONS_COLLECTED, f"{len(corrections)} total, {corrected_count} corrected")

    # ── FEW-SHOT BLOCK ────────────────────────────────────────────────────────
    few_shot = build_few_shot_block(corrections)
    example_count = len([c for c in corrections if c.action.value == "corrected"])
    _stage(PipelineStage.FEW_SHOT_BLOCK_BUILT, f"{example_count} few-shot examples built")

    # ── STAGE 6 — RECLASSIFICATION ────────────────────────────────────────────
    console.print("\n[yellow]Stage 6 — Reclassification with Few-Shot…[/yellow]")
    reclassifications = reclassify_with_fewshot(messages, classifications, corrections)
    _save(config.RECLASSIFIED_OUTPUTS_PATH, reclassifications)
    _stage(PipelineStage.RECLASSIFICATION_COMPLETE, f"{len(reclassifications)} messages reclassified")

    # ── BEFORE / AFTER COMPARISON ─────────────────────────────────────────────
    improved = sum(1 for r in reclassifications if r.improved)
    _stage(PipelineStage.BEFORE_AFTER_COMPARISON_COMPLETE, f"{improved}/{len(reclassifications)} improved")

    # ── STAGE 7 — ANALYTICS ───────────────────────────────────────────────────
    console.print("\n[yellow]Stage 7 — Analytics…[/yellow]")
    analytics = generate_analytics(classifications, risk_scores, compliance, corrections, reclassifications)
    _save(config.ANALYTICS_SUMMARY_PATH, analytics)
    _stage(PipelineStage.ANALYTICS_GENERATED)

    # ── STAGE 8 — ROUTING ─────────────────────────────────────────────────────
    console.print("\n[yellow]Stage 8 — Routing Decisions…[/yellow]")
    routing_decisions = generate_routing(messages, classifications, risk_scores)
    _save(config.ROUTING_DECISIONS_PATH, routing_decisions)

    # Print any critical escalation alerts
    alerts = [r for r in routing_decisions if r.alert_triggered and r.alert_message]
    if alerts:
        console.print("\n")
        for r in alerts:
            console.print(Panel(r.alert_message, style="bold red", box=box.HEAVY))

    # ── BUILD triage_output.json ──────────────────────────────────────────────
    cls_map      = {c.id: c for c in classifications}
    risk_map     = {r.id: r for r in risk_scores}
    draft_map    = {d.id: d for d in drafts}
    comp_map     = {c.id: c for c in compliance}
    reclass_map  = {r.id: r for r in reclassifications}
    routing_map  = {r.id: r for r in routing_decisions}
    corr_map     = {c.id: c for c in corrections}

    triage_output = []
    for msg in messages:
        cls    = cls_map.get(msg.id)
        risk   = risk_map.get(msg.id)
        draft  = draft_map.get(msg.id)
        comp   = comp_map.get(msg.id)
        recls  = reclass_map.get(msg.id)
        route  = routing_map.get(msg.id)
        corr   = corr_map.get(msg.id)

        triage_output.append(TriageRecord(
            id=msg.id,
            message=msg.message,
            initial_category=cls.category if cls else "product_query",
            initial_confidence=cls.confidence if cls else 0.0,
            needs_human_review=cls.needs_human_review if cls else False,
            risk_level=risk.risk_level if risk else "medium",
            draft_response=draft.draft_response if draft else "",
            compliance_passed=comp.passed if comp else True,
            compliance_violations=comp.violations if comp else [ComplianceViolation.none],
            reclassified_category=recls.reclassified_category if recls else (cls.category if cls else "product_query"),
            reclassified_confidence=recls.confidence_after if recls else (cls.confidence if cls else 0.0),
            routing_team=route.team if route else "",
            routing_sla=route.sla if route else "",
            routing_escalation_path=route.escalation_path if route else "",
            operator_action=corr.action if corr else None,
            corrected_category=corr.corrected_category if corr else None,
            improved=recls.improved if recls else False,
        ))

    _save(config.TRIAGE_OUTPUT_PATH, triage_output)

    # ── VALIDATION ────────────────────────────────────────────────────────────
    _stage(PipelineStage.VALIDATION_COMPLETE, "Run  python validate.py  to validate all artifacts")

    # ── RESULTS_FINALISED ─────────────────────────────────────────────────────
    _stage(PipelineStage.RESULTS_FINALISED, "Pipeline complete!")

    high_risk_count = (
        analytics["risk_distribution"].get("high", 0)
        + analytics["risk_distribution"].get("critical", 0)
    )
    console.print(Panel(
        f"[bold]Pipeline Summary[/bold]\n"
        f"Messages processed  : {len(messages)}\n"
        f"Human review flagged: {analytics['human_review_count']}\n"
        f"High / Critical risk: {high_risk_count}\n"
        f"Compliance failures : {analytics['compliance_failure_count']}\n"
        f"Corrections applied : {analytics['correction_count']}\n"
        f"Accuracy delta      : {analytics['accuracy_delta']:+.2%}",
        box=box.ROUNDED,
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fintech AI Support Triage Pipeline")
    parser.add_argument("--auto", action="store_true", help="Auto-accept all corrections (CI mode)")
    args = parser.parse_args()
    main(auto_accept=args.auto)