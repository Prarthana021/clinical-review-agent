from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.audit import (
    AuditLogError,
    InvalidReviewerActionError,
    ReviewNotFoundError,
    audit_repository,
)
from backend.app.cases import CaseDataError, CaseNotFoundError, case_repository
from backend.app.review_engine import DeterministicReviewEngine


app = FastAPI(
    title="Clinical Review Agent API",
    description="Backend API for synthetic clinical review case loading.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):517[0-9]",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
review_engine = DeterministicReviewEngine(case_repository)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cases")
def list_cases() -> list[dict]:
    try:
        return case_repository.list_cases()
    except CaseDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    try:
        return case_repository.get_public_case(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CaseDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reviews")
def create_review(payload: dict) -> dict:
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="Missing required field: case_id")

    try:
        review_result = review_engine.review_case(case_id)
        return audit_repository.save_review_result(review_result)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CaseDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AuditLogError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reviews/{review_id}/decision")
def save_reviewer_decision(review_id: str, payload: dict) -> dict:
    action = payload.get("action")
    if not action:
        raise HTTPException(status_code=400, detail="Missing required field: action")

    comment = payload.get("comment", "")
    reviewer_id = payload.get("reviewer_id", "demo-reviewer")

    try:
        return audit_repository.save_reviewer_decision(
            review_id=review_id,
            action=action,
            comment=comment,
            reviewer_id=reviewer_id,
        )
    except InvalidReviewerActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditLogError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/audit")
def list_audit_records() -> list[dict]:
    try:
        return audit_repository.list_audit_records()
    except AuditLogError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
