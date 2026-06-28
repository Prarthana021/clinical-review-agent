# Backend

FastAPI backend for Clinical Review Agent.

This first backend slice only loads synthetic case data from `data/` and exposes basic case endpoints.

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

The first tests use only the Python standard library so they can run before dependencies are installed:

```bash
python3 -m unittest discover backend/tests
```

## Current Endpoints

- `GET /health`
- `GET /cases`
- `GET /cases/{case_id}`

The public case response intentionally excludes `expected_result.json`. Expected results are for internal evaluation only and should not appear in the main demo flow.

