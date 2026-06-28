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
