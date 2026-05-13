from typing import List
from ..schemas import SupportMessage, ClassificationResult

RISK_SYSTEM = """You are a fintech risk assessment specialist. Score support messages for operational risk.

Risk levels (use exactly as written): low, medium, high, critical

Triggering criteria to detect:
- chargeback intent        : customer threatening to reverse charges with bank
- scam accusations         : customer claims they were defrauded on platform
- fraud claims             : unauthorized account activity reported
- legal threats            : mentions of lawyers, lawsuits, court, or legal action
- regulator complaints     : mentions of FCA, SEC, FINRA, FSB, or other regulators
- withdrawal urgency       : demands immediate access to funds
- frozen funds             : account or funds inaccessible without explanation
- account suspension       : account disabled/restricted without prior notice
- financial loss claims    : significant reported monetary loss
- compliance sensitivity   : AML/KYC, sanctions, GDPR exposure

You MUST respond with a valid JSON array only — no markdown, no explanation."""


def build_risk_scoring_prompt(
    messages: List[SupportMessage],
    classifications: List[ClassificationResult],
) -> str:
    cls_map = {c.id: c for c in classifications}
    lines = []
    for m in messages:
        cls = cls_map.get(m.id)
        cat = cls.category.value if cls else "unknown"
        lines.append(f'ID {m.id} [category: {cat}]: "{m.message}"')

    messages_block = "\n".join(lines)
    return f"""Assess risk for {len(messages)} fintech support messages.

Messages:
{messages_block}

Respond with a JSON array in this exact format:
[
  {{
    "id": 14,
    "risk_level": "critical",
    "triggering_criteria": ["legal threats", "regulator complaints"],
    "rationale": "Customer explicitly mentions FCA complaint and legal action."
  }}
]"""