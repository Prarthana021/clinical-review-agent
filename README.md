# Clinical Review Agent

Clinical Review Agent will be a synthetic medical review copilot for checking whether a submitted claim diagnosis is supported by chart evidence.
It will use graph-based evidence retrieval, deterministic validation, and AI-generated explanations to prepare review packages for a human reviewer.
This project is a proof of concept and will not be used for real clinical, coding, payment, or compliance decisions.

## What Works Now

- Three synthetic clinical review cases.
- FastAPI backend with case loading, review execution, audit logging, evaluation, and graph endpoints.
- LangGraph workflow for the review path.
- Deterministic rule-based status decisions.
- Cached AI-style explanation fallback.
- React frontend with case selection, review results, evidence cards, evidence graph, reviewer actions, audit history, and evaluation results.

## Requirements

- Python 3.12 recommended.
- Node.js 20 or newer recommended.
- npm.

No paid API key is required for the current MVP. The app currently uses prepared synthetic graph data and cached explanation fallback.

## Backend Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Useful API checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/cases
curl http://127.0.0.1:8000/evaluation
```

## Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://127.0.0.1:5173
```

## Run Tests

Backend:

```bash
source .venv/bin/activate
python -m unittest discover backend/tests
```

Frontend build check:

```bash
cd frontend
npm run build
```

## Graph Provider

The default graph provider is prepared JSON data:

```bash
GRAPH_PROVIDER=prepared_json
```

A Neo4j provider boundary exists for future work, but live Neo4j retrieval is not implemented yet.

## Model Provider

The default model provider is cached fallback:

```bash
MODEL_PROVIDER=cached
```

Live MedGemma mode is optional. It requires Hugging Face model access, enough local compute to load the model, and extra Python dependencies:

```bash
source .venv/bin/activate
pip install -r backend/requirements-medgemma.txt
export MODEL_PROVIDER=medgemma
export MEDGEMMA_MODEL_ID=google/medgemma-1.5-4b-it
export HF_TOKEN=your_hugging_face_token_if_needed
uvicorn backend.app.main:app --reload
```

If MedGemma is unavailable, the app falls back to cached explanations. The deterministic review rules still decide the status.

## Demo Script

Use [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a short guided demo flow.
