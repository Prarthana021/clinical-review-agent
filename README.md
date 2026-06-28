# Clinical Review Agent

Clinical Review Agent is a proof-of-concept medical review copilot for synthetic insurance claim and chart review scenarios.

The project demonstrates how graph-based retrieval, deterministic policy rules, a medically specialized language model, and human review can work together to prepare an evidence-cited review package for a submitted diagnosis.

## Goal

Build a small, reliable demo that helps a reviewer answer:

> Does the synthetic medical record support the diagnosis submitted on the claim?

The MVP focuses on one combined diagnosis:

**Type 2 diabetes mellitus with chronic kidney disease stage 3**

## Important Disclaimer

All data, policies, claims, notes, lab results, and outputs in this repository are synthetic. This project is not intended for real clinical, coding, payment, compliance, or medical decision-making.

## Planned MVP

The MVP will include:

- Three synthetic review cases.
- FastAPI backend.
- React frontend.
- Graph-based evidence retrieval.
- Deterministic policy and citation validation.
- Cached AI explanation fallback.
- Human reviewer action workflow.
- SQLite audit logging.

## Development Approach

This project will be built in small reviewable steps:

1. Public repo skeleton and planning docs.
2. Synthetic case data.
3. Backend case loader.
4. Deterministic review engine.
5. Frontend case selection.
6. Review workspace.
7. Audit logging.
8. Graph visualization.
9. Optional live MedGemma and Neo4j integration.

Each step should be tested, reviewed, committed, and pushed before moving on.

## Repository Structure

```text
backend/        FastAPI service, review workflow, validation, audit log
frontend/       React reviewer interface
data/           Synthetic patient cases and policies
docs/           Public component plans and implementation notes
```

## Planning Docs

- [Backend Plan](docs/BACKEND_PLAN.md)
- [Frontend Plan](docs/FRONTEND_PLAN.md)
- [AI and Graph Plan](docs/AI_GRAPH_PLAN.md)
- [Demo Cases Plan](docs/DEMO_CASES_PLAN.md)

