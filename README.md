# Clinical Review Agent

Clinical Review Agent will be a synthetic medical review copilot for checking whether a submitted claim diagnosis is supported by chart evidence.
It will use graph-based evidence retrieval, deterministic validation, and AI-generated explanations to prepare review packages for a human reviewer.
This project is a proof of concept and will not be used for real clinical, coding, payment, or compliance decisions.

## What Works Now

- Three synthetic clinical review cases.
- FastAPI backend with case loading, review execution, audit logging, evaluation, and graph endpoints.
- LangGraph workflow for the review path, including conditional retry/escalation branches.
- Runtime entity/relation extraction from claim, note, lab, and policy text. In live MedGemma mode, MedGemma proposes the semantic review edges and Python validates them before Neo4j stores them.
- ChromaDB local vector retrieval over synthetic notes and labs.
- Neo4j graph provider implementation for live graph retrieval when configured.
- Deterministic rule-based status decisions.
- Optional MedGemma explanation adapter with cached fallback.
- React frontend with claim selection, local file intake, review results, evidence cards, evidence trace, reviewer actions, and audit history.

## Requirements

- Python 3.12 recommended.
- Node.js 20 or newer recommended.
- npm.

No paid API key is required for the default local MVP. The app uses prepared synthetic graph data, local ChromaDB vector retrieval, and cached explanation fallback unless live MedGemma is configured.

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
curl http://127.0.0.1:8000/capabilities
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

Live Neo4j retrieval is implemented, but you must provide a running Neo4j instance:

```bash
export GRAPH_PROVIDER=neo4j
export NEO4J_URI=neo4j://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password
uvicorn backend.app.main:app --reload
```

In Neo4j mode, the backend upserts the selected synthetic case graph into Neo4j and retrieves evidence relationships with Cypher.

The review relationships are generated at runtime from case text before they are written to Neo4j. The graph nodes come from the case schema, while review edges such as `DOCUMENTS`, `SUPPORTS_RELATIONSHIP`, `CONTRADICTS`, `WEAKENS`, and `SATISFIES` are extracted when the case loads.

When `MODEL_PROVIDER=local_http`, MedGemma through LM Studio performs the semantic edge extraction. Python validates that MedGemma only returned allowed relationship types and real node IDs before those edges are written to Neo4j. In default test mode, the app uses deterministic extraction so automated tests do not require a running local model server.

## Vector Provider

The default vector provider is local ChromaDB:

```bash
VECTOR_PROVIDER=chromadb
```

ChromaDB indexes note and lab text under `runtime/chroma/` and returns semantic evidence IDs to the LangGraph workflow. No cloud vector database account is required.

## Model Provider

The default model provider is cached fallback:

```bash
MODEL_PROVIDER=cached
```

For a Mac-friendly MedGemma setup, run a quantized MedGemma 4B model in LM Studio or another OpenAI-compatible local server, then point the backend at that local server:

```bash
export MODEL_PROVIDER=local_http
export LOCAL_LLM_BASE_URL=http://127.0.0.1:1234
export LOCAL_LLM_MODEL=medgemma-1.5-4b-it
uvicorn backend.app.main:app --reload
```

LM Studio usually runs at `http://127.0.0.1:1234`; the backend adds the OpenAI-compatible `/v1/chat/completions` path automatically. Use the exact model name shown in LM Studio for `LOCAL_LLM_MODEL`. This mode avoids loading MedGemma directly inside Python.

Full Python MedGemma mode is also available, but it requires Hugging Face model access, enough local compute to load the model, and extra Python dependencies:

```bash
source .venv/bin/activate
pip install -r backend/requirements-medgemma.txt
export MODEL_PROVIDER=medgemma
export MEDGEMMA_MODEL_ID=google/medgemma-1.5-4b-it
export HF_TOKEN=your_hugging_face_token_if_needed
uvicorn backend.app.main:app --reload
```

If the local model server or full Python MedGemma is unavailable, the app falls back to cached explanations. The deterministic review rules still decide the status.

The model explains the rule result; it does not decide the final review status. Each review records the model mode, model name, proposed status, deterministic rule result, citation validation result, policy version, evidence IDs, and graph paths.

Check the active configuration:

```bash
curl http://127.0.0.1:8000/capabilities
```

## Demo Script

Use [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) for a short guided demo flow.
