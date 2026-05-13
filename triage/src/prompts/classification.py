from typing import List
from ..schemas import SupportMessage

CLASSIFICATION_SYSTEM = """You are a senior fintech support triage AI. Classify customer support messages.

Allowed categories (use exactly as written):
- payments       : deposits, withdrawals, transfers, billing, chargebacks
- technical      : platform bugs, API errors, login issues, connectivity
- compliance     : KYC/AML, regulatory inquiries, audit reports, policy violations
- account        : account settings, profile, closures, verification, KYC uploads
- product_query  : questions about features, pricing, trading hours, products
- escalation     : legal threats, fraud allegations, regulator complaints, urgent loss

Rules:
1. Assign exactly ONE category per message.
2. confidence is a float between 0.0 and 1.0.
3. If confidence < 0.7, set needs_human_review to true, otherwise false.
4. reason must be under 20 words.

You MUST respond with a valid JSON array only — no markdown, no explanation."""


def build_classification_prompt(messages: List[SupportMessage], few_shot_examples: str = "") -> str:
    lines = [f'ID {m.id}: "{m.message}"' for m in messages]
    messages_block = "\n".join(lines)

    few_shot_block = ""
    if few_shot_examples:
        few_shot_block = (
            "\n\nOperator-corrected examples (use these to improve accuracy):\n"
            + few_shot_examples
            + "\n"
        )

    return f"""Classify the following {len(messages)} fintech support messages into exactly one category each.{few_shot_block}

Messages:
{messages_block}

Respond with a JSON array in this exact format:
[
  {{
    "id": 1,
    "category": "payments",
    "confidence": 0.86,
    "needs_human_review": false,
    "reason": "Delayed deposit issue."
  }}
]"""