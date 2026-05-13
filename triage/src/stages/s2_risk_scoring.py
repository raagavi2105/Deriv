from typing import Dict, List

from groq import Groq

from .. import config
from ..llm_logger import log_llm_call
from ..prompts.risk_scoring import RISK_SYSTEM, build_risk_scoring_prompt
from ..schemas import Category, ClassificationResult, RiskLevel, RiskScore, SupportMessage
from ..utils import extract_json, with_retry

_DETERMINISTIC_MAP: Dict[Category, RiskLevel] = {
    Category.product_query: RiskLevel.low,
    Category.technical:     RiskLevel.medium,
    Category.account:       RiskLevel.medium,
    Category.payments:      RiskLevel.medium,
    Category.compliance:    RiskLevel.high,
    Category.escalation:    RiskLevel.high,
}


def _deterministic(msg_id: int, category: Category) -> RiskScore:
    level = _DETERMINISTIC_MAP.get(category, RiskLevel.medium)
    return RiskScore(
        id=msg_id,
        risk_level=level,
        triggering_criteria=[],
        rationale=f"Deterministic mapping: {category.value} → {level.value}",
    )


@with_retry(max_attempts=3, delay=2.0)
def score_risks(
    messages: List[SupportMessage],
    classifications: List[ClassificationResult],
) -> List[RiskScore]:
    cls_map: Dict[int, ClassificationResult] = {c.id: c for c in classifications}

    llm_messages = [
        m for m in messages
        if (cls := cls_map.get(m.id)) and (
            cls.category == Category.escalation or cls.needs_human_review
        )
    ]
    deterministic_ids = [m.id for m in messages if m.id not in {m2.id for m2 in llm_messages}]

    results: Dict[int, RiskScore] = {}

    # Deterministic scoring for low-ambiguity messages
    for mid in deterministic_ids:
        cls = cls_map.get(mid)
        cat = cls.category if cls else Category.product_query
        results[mid] = _deterministic(mid, cat)

    # LLM scoring for escalations and human-review messages
    if llm_messages:
        client = Groq(api_key=config.GROQ_API_KEY)
        prompt = build_risk_scoring_prompt(llm_messages, classifications)

        response = client.chat.completions.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            messages=[
                {"role": "system", "content": RISK_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or ""
        data = extract_json(raw)
        if isinstance(data, dict):
            data = next(iter(data.values()))

        for item in data:
            results[item["id"]] = RiskScore(
                id=item["id"],
                risk_level=item["risk_level"],
                triggering_criteria=item.get("triggering_criteria", []),
                rationale=item.get("rationale", ""),
            )

        log_llm_call(
            stage="risk_scoring",
            prompt=prompt,
            output_artifact=str(config.RISK_SCORES_PATH),
            input_artifacts=[str(config.INITIAL_CLASSIFICATIONS_PATH)],
        )

    # Fallback for any IDs still missing
    for m in messages:
        if m.id not in results:
            cls = cls_map.get(m.id)
            results[m.id] = _deterministic(m.id, cls.category if cls else Category.product_query)

    return [results[m.id] for m in messages]