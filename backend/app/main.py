from __future__ import annotations

from fastapi import FastAPI, HTTPException

from backend.app.cases import CaseDataError, CaseNotFoundError, case_repository
from backend.app.review_engine import DeterministicReviewEngine


app = FastAPI(
    title="Clinical Review Agent API",
    description="Backend API for synthetic clinical review case loading.",
    version="0.1.0",
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
        return review_engine.review_case(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CaseDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
