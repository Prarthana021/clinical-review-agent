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

