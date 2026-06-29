from __future__ import annotations

from typing import Literal, TypedDict


AIStatus = Literal[
    "supported",
    "unsupported",
    "contradicted",
    "insufficient_evidence",
    "requires_expert_review",
]

ReviewerAction = Literal[
    "approve",
    "reject",
    "request_documentation",
    "escalate",
]


class CaseSummaryResponse(TypedDict):
    id: str
    patient_id: str
    patient_name: str
    review_year: int
    submitted_diagnosis: str
    title: str


class ReviewResultResponse(TypedDict):
    review_id: str
    case_id: str
    status: AIStatus
    rule_result: AIStatus
    submitted_diagnosis: str
    supporting_evidence_ids: list[str]
    contradictory_evidence_ids: list[str]
    satisfied_requirement_ids: list[str]
    missing_requirement_ids: list[str]
    graph_paths: list[dict]
    explanation: str
    validation: dict


class ReviewerDecisionRequest(TypedDict, total=False):
    action: ReviewerAction
    comment: str
    reviewer_id: str


class AuditRecordResponse(TypedDict):
    audit_id: str
    review_id: str
    case_id: str
    submitted_diagnosis: str
    ai_status: AIStatus
    rule_result: AIStatus
    supporting_evidence_ids: list[str]
    contradictory_evidence_ids: list[str]
    graph_paths: list[dict]
    llm_explanation: str
    validation: dict
    reviewer_action: ReviewerAction
    reviewer_comment: str
    reviewer_id: str
    decided_at: str
