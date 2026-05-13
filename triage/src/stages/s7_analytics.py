from collections import Counter
from typing import Dict, List, Optional

from ..schemas import (
    ClassificationResult,
    ComplianceResult,
    CorrectionAction,
    OperatorCorrection,
    ReclassificationResult,
    RiskScore,
)


def generate_analytics(
    classifications: List[ClassificationResult],
    risk_scores: List[RiskScore],
    compliance_results: List[ComplianceResult],
    corrections: List[OperatorCorrection],
    reclassifications: List[ReclassificationResult],
) -> Dict:
    total = len(classifications)

    category_distribution = dict(Counter(c.category.value for c in classifications))
    avg_confidence = round(
        sum(c.confidence for c in classifications) / total, 4
    ) if total else 0.0

    risk_distribution = dict(Counter(r.risk_level.value for r in risk_scores))
    human_review_count = sum(1 for c in classifications if c.needs_human_review)
    correction_count   = sum(1 for c in corrections if c.action == CorrectionAction.corrected)
    compliance_failure_count = sum(1 for r in compliance_results if not r.passed)

    # Most common correction target
    corrected = [c for c in corrections if c.action == CorrectionAction.corrected and c.corrected_category]
    most_common_correction: Optional[str] = None
    if corrected:
        most_common_correction = Counter(c.corrected_category.value for c in corrected).most_common(1)[0][0]

    # Accuracy delta — computed over messages that had operator corrections
    corrected_ids = {c.id for c in corrections if c.action == CorrectionAction.corrected}
    accuracy_before = accuracy_after = accuracy_delta = 0.0

    if corrected_ids and reclassifications:
        relevant = [r for r in reclassifications if r.id in corrected_ids]
        if relevant:
            accuracy_before = round(
                sum(1 for r in relevant if r.original_category == r.corrected_label) / len(relevant), 4
            )
            accuracy_after = round(
                sum(1 for r in relevant if r.reclassified_category == r.corrected_label) / len(relevant), 4
            )
            accuracy_delta = round(accuracy_after - accuracy_before, 4)

    improvement_count = sum(1 for r in reclassifications if r.improved)

    return {
        "total_messages":          total,
        "category_distribution":   category_distribution,
        "average_confidence":      avg_confidence,
        "risk_distribution":       risk_distribution,
        "human_review_count":      human_review_count,
        "correction_count":        correction_count,
        "compliance_failure_count": compliance_failure_count,
        "accuracy_before":         accuracy_before,
        "accuracy_after":          accuracy_after,
        "accuracy_delta":          accuracy_delta,
        "improvement_count":       improvement_count,
        "most_common_correction":  most_common_correction,
    }