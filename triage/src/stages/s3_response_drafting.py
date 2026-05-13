from typing import Dict, List

from groq import Groq

from .. import config
from ..llm_logger import log_llm_call
from ..prompts.response_drafting import (
    BATCH_DRAFTING_SYSTEM,
    HIGH_RISK_SYSTEM,
    build_batch_drafting_prompt,
    build_high_risk_draft_prompt,
)
from ..schemas import DraftResponse, RiskLevel, RiskScore, SupportMessage
from ..utils import extract_json, with_retry

_HIGH_RISK = {RiskLevel.high, RiskLevel.critical}


@with_retry(max_attempts=3, delay=2.0)
def draft_responses(
    messages: List[SupportMessage],
    risk_scores: List[RiskScore],
) -> List[DraftResponse]:
    risk_map: Dict[int, RiskScore] = {r.id: r for r in risk_scores}
    client = Groq(api_key=config.GROQ_API_KEY)

    low_medium  = [m for m in messages if risk_map.get(m.id) and risk_map[m.id].risk_level not in _HIGH_RISK]
    high_critical = [m for m in messages if risk_map.get(m.id) and risk_map[m.id].risk_level in _HIGH_RISK]

    results: Dict[int, DraftResponse] = {}

    # Single batched call for low / medium risk
    if low_medium:
        prompt = build_batch_drafting_prompt(low_medium, risk_scores)
        resp = client.chat.completions.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            messages=[
                {"role": "system", "content": BATCH_DRAFTING_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        data = extract_json(resp.choices[0].message.content or "")
        if isinstance(data, dict):
            data = next(iter(data.values()))

        for item in data:
            mid = item["id"]
            results[mid] = DraftResponse(
                id=mid,
                risk_level=risk_map[mid].risk_level,
                draft_response=item["draft_response"],
                drafting_mode="batched",
            )
        log_llm_call(
            stage="drafting",
            prompt=prompt,
            output_artifact=str(config.DRAFT_RESPONSES_PATH),
            input_artifacts=[str(config.RISK_SCORES_PATH)],
            risk_tier="low/medium",
        )

    # Individual calls per high / critical message
    for m in high_critical:
        risk = risk_map[m.id]
        prompt = build_high_risk_draft_prompt(m, risk)
        resp = client.chat.completions.create(
            model=config.MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": HIGH_RISK_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        item = extract_json(resp.choices[0].message.content or "")
        if isinstance(item, list):
            item = item[0]

        results[m.id] = DraftResponse(
            id=m.id,
            risk_level=risk.risk_level,
            draft_response=item["draft_response"],
            drafting_mode="individual",
        )
        log_llm_call(
            stage="drafting",
            prompt=prompt,
            output_artifact=str(config.DRAFT_RESPONSES_PATH),
            input_artifacts=[str(config.RISK_SCORES_PATH)],
            risk_tier=risk.risk_level.value,
            message_id=m.id,
        )

    return [results[m.id] for m in messages if m.id in results]