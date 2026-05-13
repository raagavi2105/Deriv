from typing import List

from ..schemas import (
    ClassificationResult,
    CorrectionAction,
    OperatorCorrection,
    ReclassificationResult,
    SupportMessage,
)
from .s1_classification import classify_messages


def build_few_shot_block(corrections: List[OperatorCorrection]) -> str:
    """Build few-shot examples from operator-corrected messages (max 10)."""
    examples = []
    for c in corrections:
        if c.action == CorrectionAction.corrected and c.corrected_category:
            examples.append(
                f'Message: "{c.message}"\n'
                f'Correct category: {c.corrected_category.value}\n'
                f'(Was misclassified as: {c.original_category.value})'
            )
    return "\n\n".join(examples[:10])


def reclassify_with_fewshot(
    messages: List[SupportMessage],
    initial_classifications: List[ClassificationResult],
    corrections: List[OperatorCorrection],
) -> List[ReclassificationResult]:
    few_shot_block = build_few_shot_block(corrections)
    new_classifications = classify_messages(messages, few_shot_examples=few_shot_block, is_reclassification=True)

    initial_map    = {c.id: c for c in initial_classifications}
    correction_map = {
        c.id: c for c in corrections
        if c.action == CorrectionAction.corrected
    }

    results: List[ReclassificationResult] = []
    for new_cls in new_classifications:
        initial    = initial_map.get(new_cls.id)
        correction = correction_map.get(new_cls.id)
        corrected_label = correction.corrected_category if correction else None

        if corrected_label:
            improved = new_cls.category == corrected_label
        elif initial:
            improved = new_cls.confidence > initial.confidence
        else:
            improved = False

        results.append(ReclassificationResult(
            id=new_cls.id,
            original_category=initial.category if initial else new_cls.category,
            corrected_label=corrected_label,
            reclassified_category=new_cls.category,
            confidence_before=initial.confidence if initial else 0.0,
            confidence_after=new_cls.confidence,
            improved=improved,
        ))

    return results