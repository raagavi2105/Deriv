from typing import Dict, List

from .. import config
from ..schemas import (
    Category,
    ClassificationResult,
    RiskLevel,
    RoutingDecision,
    RiskScore,
    SupportMessage,
)


def _escalation_alert(
    msg: SupportMessage,
    risk: RiskScore,
    cls: ClassificationResult,
    routing: Dict,
) -> str:
    criteria = ", ".join(risk.triggering_criteria) if risk.triggering_criteria else "N/A"
    snippet  = msg.message[:180] + ("..." if len(msg.message) > 180 else "")
    return (
        "🚨 CRITICAL ESCALATION ALERT 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Message ID   : {msg.id}\n"
        f"Risk Level   : {risk.risk_level.value.upper()}\n"
        f"Category     : {cls.category.value}\n"
        f"Assigned To  : {routing['team']}\n"
        f"SLA          : {routing['sla']}\n"
        f"Escalate To  : {routing['escalation_path']}\n"
        f"Criteria     : {criteria}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Message      : {snippet}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def generate_routing(
    messages: List[SupportMessage],
    classifications: List[ClassificationResult],
    risk_scores: List[RiskScore],
) -> List[RoutingDecision]:
    cls_map:  Dict[int, ClassificationResult] = {c.id: c for c in classifications}
    risk_map: Dict[int, RiskScore]            = {r.id: r for r in risk_scores}

    results: List[RoutingDecision] = []
    for msg in messages:
        cls        = cls_map.get(msg.id)
        risk       = risk_map.get(msg.id)
        category   = cls.category  if cls  else Category.product_query
        risk_level = risk.risk_level if risk else RiskLevel.medium

        routing_info  = config.ROUTING_MATRIX.get(category.value, config.ROUTING_MATRIX["product_query"])
        alert_triggered = risk_level in (RiskLevel.high, RiskLevel.critical)
        alert_message   = _escalation_alert(msg, risk, cls, routing_info) if (alert_triggered and risk and cls) else None

        results.append(RoutingDecision(
            id=msg.id,
            category=category,
            risk_level=risk_level,
            team=routing_info["team"],
            sla=routing_info["sla"],
            escalation_path=routing_info["escalation_path"],
            alert_triggered=alert_triggered,
            alert_message=alert_message,
        ))

    return results