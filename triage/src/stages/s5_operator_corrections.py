import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .. import config
from ..schemas import (
    Category,
    ClassificationResult,
    CorrectionAction,
    OperatorCorrection,
    RiskScore,
    SupportMessage,
)

console = Console()

_CATEGORY_MENU: Dict[str, Category] = {
    "1": Category.payments,
    "2": Category.technical,
    "3": Category.compliance,
    "4": Category.account,
    "5": Category.product_query,
    "6": Category.escalation,
}


def _load_existing() -> Dict[int, OperatorCorrection]:
    existing: Dict[int, OperatorCorrection] = {}
    if not config.CORRECTIONS_FILE.exists():
        return existing
    with open(config.CORRECTIONS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    existing_corr = OperatorCorrection(**json.loads(line))
                    existing[existing_corr.id] = existing_corr
                except Exception:
                    pass
    return existing


def _persist(correction: OperatorCorrection) -> None:
    with open(config.CORRECTIONS_FILE, "a") as f:
        f.write(correction.model_dump_json() + "\n")


def collect_corrections(
    messages: List[SupportMessage],
    classifications: List[ClassificationResult],
    risk_scores: List[RiskScore],
    auto_accept: bool = False,
) -> List[OperatorCorrection]:
    existing = _load_existing()
    cls_map: Dict[int, ClassificationResult] = {c.id: c for c in classifications}
    risk_map: Dict[int, RiskScore] = {r.id: r for r in risk_scores}

    reviewable = [m for m in messages if m.id not in existing]

    if not reviewable or auto_accept:
        if auto_accept and reviewable:
            # Auto-accept all unreviewed messages without prompting
            new_corrections: List[OperatorCorrection] = []
            for msg in reviewable:
                cls = cls_map.get(msg.id)
                corr = OperatorCorrection(
                    id=msg.id,
                    message=msg.message,
                    original_category=cls.category if cls else Category.product_query,
                    corrected_category=None,
                    action=CorrectionAction.accepted,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                _persist(corr)
                new_corrections.append(corr)
            return list(existing.values()) + new_corrections

        if not reviewable:
            console.print("[green]All messages reviewed in prior runs. Skipping.[/green]")
        return list(existing.values())

    console.print(Panel(
        f"[bold cyan]OPERATOR CORRECTION INTERFACE[/bold cyan]\n"
        f"Reviewing [yellow]{len(reviewable)}[/yellow] of {len(messages)} messages\n"
        f"[dim]({len(existing)} already reviewed in prior runs)[/dim]",
        box=box.DOUBLE,
    ))

    new_corrections = []
    for i, msg in enumerate(reviewable, 1):
        cls  = cls_map.get(msg.id)
        risk = risk_map.get(msg.id)

        tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        tbl.add_column("Field", style="bold yellow", width=20)
        tbl.add_column("Value")

        tbl.add_row("Message",       msg.message)
        tbl.add_row("Category",      cls.category.value if cls else "—")
        tbl.add_row("Confidence",    f"{cls.confidence:.2f}" if cls else "—")
        tbl.add_row("Needs Review",  "[red]YES[/red]" if (cls and cls.needs_human_review) else "no")
        tbl.add_row("Risk Level",    f"[{'red' if risk and risk.risk_level.value in ('high','critical') else 'yellow'}]{risk.risk_level.value.upper()}[/]" if risk else "—")
        tbl.add_row("Reason",        cls.reason if cls else "—")

        console.print(Panel(
            tbl,
            title=f"[bold]Message [{i}/{len(reviewable)}]  —  ID {msg.id}[/bold]",
            box=box.ROUNDED,
        ))

        raw_action = Prompt.ask(
            "  [A]ccept  [C]orrect  [S]kip",
            choices=["a", "c", "s", "A", "C", "S"],
            default="a",
        ).lower()

        corrected_category: Optional[Category] = None
        action: CorrectionAction

        if raw_action == "c":
            console.print("\n  Select correct category:")
            for k, v in _CATEGORY_MENU.items():
                console.print(f"    [cyan]{k}[/cyan] → {v.value}")
            cat_key = Prompt.ask("  Category number", choices=list(_CATEGORY_MENU.keys()))
            corrected_category = _CATEGORY_MENU[cat_key]
            action = CorrectionAction.corrected
        elif raw_action == "s":
            action = CorrectionAction.skipped
        else:
            action = CorrectionAction.accepted

        corr = OperatorCorrection(
            id=msg.id,
            message=msg.message,
            original_category=cls.category if cls else Category.product_query,
            corrected_category=corrected_category,
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        _persist(corr)
        new_corrections.append(corr)
        console.print(f"  [green]✓ {action.value}[/green]\n")

    return list(existing.values()) + new_corrections