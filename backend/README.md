# Backend

FastAPI backend for Clinical Review Agent.

The backend loads synthetic case data, runs a LangGraph review workflow,
retrieves relationship evidence from the prepared graph or Neo4j, retrieves
semantic evidence from local ChromaDB, applies deterministic policy rules, and
uses MedGemma or cached fallback text for the reviewer-facing explanation.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run

```bash
uvicorn backend.app.main:app --reload
```

## Test

```bash
python -m unittest discover backend/tests
```

## Current Endpoints

- `GET /health`
- `GET /capabilities`
- `GET /cases`
- `GET /cases/{case_id}`
- `GET /cases/{case_id}/graph`
- `POST /reviews`
- `POST /reviews/{review_id}/decision`
- `GET /audit`
- `GET /evaluation`

The public case response intentionally excludes `expected_result.json`. Expected results are for internal evaluation only and should not appear in the main demo flow.
