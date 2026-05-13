from typing import Dict, List

from groq import Groq

from .. import config
from ..llm_logger import log_llm_call
from ..prompts.compliance import COMPLIANCE_SYSTEM, FLAGGED_KEYWORDS, build_compliance_prompt
from ..schemas import ComplianceResult, ComplianceViolation, DraftResponse, SupportMessage
from ..utils import extract_json, with_retry


def _keyword_scan(text: str) -> List[str]:
    lower = text.lower()
    return [kw for kw in FLAGGED_KEYWORDS if kw.lower() in lower]


@with_retry(max_attempts=3, delay=2.0)
def check_compliance(
    messages: List[SupportMessage],
    drafts: List[DraftResponse],
) -> List[ComplianceResult]:
    client = Groq(api_key=config.GROQ_API_KEY)
    draft_map: Dict[int, DraftResponse] = {d.id: d for d in drafts}

    prompt = build_compliance_prompt(messages, drafts)
    response = client.chat.completions.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[
            {"role": "system", "content": COMPLIANCE_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or ""
    data = extract_json(raw)
    if isinstance(data, dict):
        data = next(iter(data.values()))

    valid_violations = {v.value for v in ComplianceViolation}
    results: List[ComplianceResult] = []

    for item in data:
        mid = item["id"]
        violations_raw: List[str] = item.get("violations", ["none"])
        violations = [
            ComplianceViolation(v)
            for v in violations_raw
            if v in valid_violations
        ] or [ComplianceViolation.none]

        # Deterministic keyword cross-check — catches what the LLM misses
        draft = draft_map.get(mid)
        if draft:
            flagged = _keyword_scan(draft.draft_response)
            if flagged and violations == [ComplianceViolation.none]:
                violations = [ComplianceViolation.promise]
                item["evidence"] = ", ".join(flagged[:3])
                item["recommended_fix"] = "Remove flagged compliance keywords from response."

        passed = all(v == ComplianceViolation.none for v in violations)
        results.append(ComplianceResult(
            id=mid,
            passed=passed,
            violations=violations,
            evidence=item.get("evidence"),
            recommended_fix=item.get("recommended_fix"),
        ))

    log_llm_call(
        stage="compliance_check",
        prompt=prompt,
        output_artifact=str(config.RESPONSE_COMPLIANCE_PATH),
        input_artifacts=[str(config.DRAFT_RESPONSES_PATH)],
    )

    return results