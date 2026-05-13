from typing import List
from ..schemas import SupportMessage, RiskScore

BATCH_DRAFTING_SYSTEM = """You are a professional fintech customer support specialist.

Draft empathetic, professional responses for support messages.
- 2–4 sentences per response
- Acknowledge the specific issue
- Compliance-safe: no promises, guarantees, timelines, or liability admissions
- Do not commit to specific outcomes or timeframes

You MUST respond with a valid JSON array only — no markdown, no explanation."""

HIGH_RISK_SYSTEM = """You are a compliance-aware fintech support specialist handling a HIGH-RISK or CRITICAL case.

STRICT COMPLIANCE RULES — FOLLOW EXACTLY:
- Do NOT promise resolution by any specific time
- Do NOT say "we will refund", "we guarantee", "within X hours/days"
- Do NOT admit liability or fault
- DO acknowledge the seriousness of the situation
- DO state that a senior specialist will review the case
- DO maintain professional, empathetic, de-escalatory tone
- Response: exactly 2–4 sentences

You MUST respond with a valid JSON object only — no markdown, no explanation."""


def build_batch_drafting_prompt(
    messages: List[SupportMessage],
    risk_scores: List[RiskScore],
) -> str:
    risk_map = {r.id: r.risk_level.value for r in risk_scores}
    lines = [f'ID {m.id} [risk: {risk_map.get(m.id, "medium")}]: "{m.message}"' for m in messages]
    messages_block = "\n".join(lines)

    return f"""Draft professional support responses for these {len(messages)} messages.

Messages:
{messages_block}

Respond with a JSON array in this exact format:
[
  {{"id": 1, "draft_response": "Thank you for reaching out..."}}
]"""


def build_high_risk_draft_prompt(message: SupportMessage, risk_score: RiskScore) -> str:
    criteria = ", ".join(risk_score.triggering_criteria) or "elevated risk indicators"
    return f"""Draft a compliance-safe response for this {risk_score.risk_level.value.upper()} risk support case.

Message ID   : {message.id}
Risk Level   : {risk_score.risk_level.value}
Risk Criteria: {criteria}
Customer     : "{message.message}"

Respond with a JSON object in this exact format:
{{"id": {message.id}, "draft_response": "..."}}"""