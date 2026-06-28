# Backend Plan

## Purpose

The backend will load synthetic cases, run the review workflow, validate citations and policy rules, and store reviewer decisions.

## Initial Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLite
- Pytest

LangGraph, Neo4j, and live MedGemma support can be added after the deterministic workflow is stable.

## First Backend Slice

Build only the case loader API:

- `GET /health`
- `GET /cases`
- `GET /cases/{case_id}`

This first slice should not include AI, graph traversal, or audit logging.

## Later Backend Slices

1. Add Pydantic models for case files.
2. Validate all synthetic JSON case data.
3. Add in-memory graph traversal.
4. Add deterministic review status rules.
5. Add cached model explanation adapter.
6. Add citation and policy validation.
7. Add reviewer decision endpoint.
8. Add SQLite audit log.
9. Add evaluation endpoint for all cases.

## Planned API

- `GET /health`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /reviews`
- `GET /reviews/{review_id}`
- `GET /reviews/{review_id}/graph`
- `POST /reviews/{review_id}/decision`
- `GET /audit`
- `POST /evaluation/run`

## Backend Rule

The backend must keep AI status separate from human reviewer action.

AI statuses:

- `supported`
- `unsupported`
- `contradicted`
- `insufficient_evidence`
- `requires_expert_review`

Human actions:

- `approve`
- `reject`
- `request_documentation`
- `escalate`

