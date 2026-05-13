from typing import List
from ..schemas import DraftResponse, SupportMessage

COMPLIANCE_SYSTEM = """You are a fintech compliance officer reviewing AI-drafted support responses.

Check each response for these violations (use exact strings):
- promise                       : commitment to a specific action or outcome
- specific_timeline             : mention of any specific time period or deadline
- liability_admission           : language that admits fault or responsibility
- non_compliant_financial_claim : unsubstantiated claims about refunds or financial outcomes

If NO violations found, set violations to ["none"] and passed to true.
If violations exist, set passed to false.

You MUST respond with a valid JSON array only — no markdown, no explanation."""

FLAGGED_KEYWORDS = [
    "will resolve",
    "will be fixed",
    "guarantee",
    "promise",
    "definitely",
    "refund you",
    "within 24 hours",
    "within 48 hours",
    "by tomorrow",
    "today",
    "immediately resolve",
    "we ensure",
    "we will",
    "you will receive",
]


def build_compliance_prompt(
    messages: List[SupportMessage],
    drafts: List[DraftResponse],
) -> str:
    msg_map = {m.id: m.message for m in messages}
    pairs = []
    for d in drafts:
        original = msg_map.get(d.id, "")
        pairs.append(
            f"ID {d.id}:\n"
            f"  Customer : \"{original}\"\n"
            f"  Response : \"{d.draft_response}\""
        )
    pairs_block = "\n\n".join(pairs)

    return f"""Review these {len(drafts)} support responses for compliance violations.

{pairs_block}

Respond with a JSON array in this exact format:
[
  {{
    "id": 1,
    "passed": true,
    "violations": ["none"],
    "evidence": null,
    "recommended_fix": null
  }}
]"""