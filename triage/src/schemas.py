from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Category(str, Enum):
    payments      = "payments"
    technical     = "technical"
    compliance    = "compliance"
    account       = "account"
    product_query = "product_query"
    escalation    = "escalation"


class RiskLevel(str, Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class ComplianceViolation(str, Enum):
    promise                      = "promise"
    specific_timeline            = "specific_timeline"
    liability_admission          = "liability_admission"
    non_compliant_financial_claim = "non_compliant_financial_claim"
    none                         = "none"


class CorrectionAction(str, Enum):
    accepted  = "accepted"
    corrected = "corrected"
    skipped   = "skipped"


class PipelineStage(str, Enum):
    INIT                          = "INIT"
    INPUTS_LOADED                 = "INPUTS_LOADED"
    PRIOR_CORRECTIONS_LOADED      = "PRIOR_CORRECTIONS_LOADED"
    INITIAL_CLASSIFICATION_COMPLETE = "INITIAL_CLASSIFICATION_COMPLETE"
    RISK_SCORING_COMPLETE         = "RISK_SCORING_COMPLETE"
    RESPONSES_DRAFTED             = "RESPONSES_DRAFTED"
    COMPLIANCE_CHECK_COMPLETE     = "COMPLIANCE_CHECK_COMPLETE"
    OPERATOR_CORRECTIONS_COLLECTED = "OPERATOR_CORRECTIONS_COLLECTED"
    FEW_SHOT_BLOCK_BUILT          = "FEW_SHOT_BLOCK_BUILT"
    RECLASSIFICATION_COMPLETE     = "RECLASSIFICATION_COMPLETE"
    BEFORE_AFTER_COMPARISON_COMPLETE = "BEFORE_AFTER_COMPARISON_COMPLETE"
    ANALYTICS_GENERATED           = "ANALYTICS_GENERATED"
    VALIDATION_COMPLETE           = "VALIDATION_COMPLETE"
    RESULTS_FINALISED             = "RESULTS_FINALISED"


class SupportMessage(BaseModel):
    id: int
    message: str


class ClassificationResult(BaseModel):
    id: int
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool
    reason: str


class RiskScore(BaseModel):
    id: int
    risk_level: RiskLevel
    triggering_criteria: List[str]
    rationale: str


class DraftResponse(BaseModel):
    id: int
    risk_level: RiskLevel
    draft_response: str
    drafting_mode: str  # "batched" or "individual"


class ComplianceResult(BaseModel):
    id: int
    passed: bool
    violations: List[ComplianceViolation]
    evidence: Optional[str] = None
    recommended_fix: Optional[str] = None


class OperatorCorrection(BaseModel):
    id: int
    message: str
    original_category: Category
    corrected_category: Optional[Category] = None
    action: CorrectionAction
    timestamp: str


class ReclassificationResult(BaseModel):
    id: int
    original_category: Category
    corrected_label: Optional[Category] = None
    reclassified_category: Category
    confidence_before: float
    confidence_after: float
    improved: bool


class RoutingDecision(BaseModel):
    id: int
    category: Category
    risk_level: RiskLevel
    team: str
    sla: str
    escalation_path: str
    alert_triggered: bool
    alert_message: Optional[str] = None


class LLMLogEntry(BaseModel):
    stage: str
    risk_tier: Optional[str] = None
    message_id: Optional[int] = None
    timestamp: str
    provider: str
    model: str
    prompt_hash: str
    input_artifacts: List[str]
    output_artifact: str
    few_shot_examples_included: bool


class TriageRecord(BaseModel):
    id: int
    message: str
    initial_category: Category
    initial_confidence: float
    needs_human_review: bool
    risk_level: RiskLevel
    draft_response: str
    compliance_passed: bool
    compliance_violations: List[ComplianceViolation]
    reclassified_category: Category
    reclassified_confidence: float
    routing_team: str
    routing_sla: str
    routing_escalation_path: str
    operator_action: Optional[CorrectionAction] = None
    corrected_category: Optional[Category] = None
    improved: bool