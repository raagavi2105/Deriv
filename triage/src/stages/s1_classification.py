from typing import List

from groq import Groq

from .. import config
from ..llm_logger import log_llm_call
from ..prompts.classification import CLASSIFICATION_SYSTEM, build_classification_prompt
from ..schemas import ClassificationResult, SupportMessage
from ..utils import extract_json, with_retry


@with_retry(max_attempts=3, delay=2.0)
def classify_messages(
    messages: List[SupportMessage],
    few_shot_examples: str = "",
    is_reclassification: bool = False,
) -> List[ClassificationResult]:
    client = Groq(api_key=config.GROQ_API_KEY)
    prompt = build_classification_prompt(messages, few_shot_examples)

    response = client.chat.completions.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[
            {"role": "system", "content": CLASSIFICATION_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or ""
    data = extract_json(raw)

    # Groq JSON mode may wrap the array under a key
    if isinstance(data, dict):
        data = next(iter(data.values()))

    results: List[ClassificationResult] = []
    for item in data:
        confidence = float(item["confidence"])
        results.append(ClassificationResult(
            id=item["id"],
            category=item["category"],
            confidence=confidence,
            needs_human_review=confidence < 0.7,
            reason=item.get("reason", ""),
        ))

    artifact = (
        str(config.RECLASSIFIED_OUTPUTS_PATH)
        if is_reclassification
        else str(config.INITIAL_CLASSIFICATIONS_PATH)
    )
    log_llm_call(
        stage="reclassification" if is_reclassification else "classification",
        prompt=prompt,
        output_artifact=artifact,
        input_artifacts=[str(config.SUPPORT_MESSAGES_PATH)],
        few_shot_examples_included=is_reclassification,
    )

    return results