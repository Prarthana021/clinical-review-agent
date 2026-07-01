# Clinical Review Agent

Clinical Review Agent is a local proof of concept for a payer-side clinical review copilot. It helps a reviewer check whether a submitted claim diagnosis is supported, contradicted, or missing documentation in chart evidence.

The current demo uses synthetic data only. It is not intended for real clinical, coding, payment, or compliance decisions.

## What It Does

- Loads a claim review with a submitted diagnosis, chart notes, labs, and policy requirements.
- Uses MedGemma through LM Studio to extract semantic clinical relationships in live mode.
- Stores and retrieves validated evidence relationships in Neo4j.
- Uses ChromaDB for semantic retrieval over note and lab text.
- Runs a LangGraph workflow for agent orchestration, retry/escalation paths, and citation validation.
- Uses MedGemma to explain the result in reviewer-friendly language.
- Lets a human reviewer approve, reject, request documentation, or escalate.
- Saves the review and human action in a local SQLite audit log.

## Tech Stack
- React
- TypeScript
- Python
- FastAPI
- LangGraph
- SQLite

- MedGemma 1.5 4B through LM Studio local server
- Neo4j Aura for relationship graph storage/retrieval
- ChromaDB for local vector retrieval

Local runtime data:
- `runtime/chroma/` for ChromaDB
- `runtime/audit.sqlite3` for audit history
- `.env` for private local configuration

## Local Dependencies

This project is not currently hosted in the cloud. To run the full live setup locally, you need:

- Python environment for FastAPI backend
- Node/npm for React frontend
- LM Studio running MedGemma locally
- Neo4j Aura instance for live graph storage
- ChromaDB, created automatically by the backend
- SQLite audit database, created automatically by the backend

ChromaDB and SQLite do not need separate accounts or manual setup.

## Environment Setup

Copy the example file:

```bash
cp .env.example .env
```

Fill in your private Neo4j values inside `.env`.

The real `.env` file is ignored by git. Do not commit secrets.

Example live `.env` shape:

```bash
MODEL_PROVIDER=local_http
RELATION_EXTRACTOR_PROVIDER=medgemma_local_http
GRAPH_PROVIDER=neo4j
VECTOR_PROVIDER=chromadb

LOCAL_LLM_BASE_URL=http://127.0.0.1:1234
LOCAL_LLM_MODEL=medgemma-1.5-4b-it

NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=your_neo4j_user
NEO4J_PASSWORD=your_neo4j_password
```

## Run Backend

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

set -a
source .env
set +a

uvicorn backend.app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Useful checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/capabilities
curl http://127.0.0.1:8000/cases
```

## Run Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually:

```text
http://127.0.0.1:5173
```

## LM Studio Setup

1. Open LM Studio.
2. Download/load `medgemma-1.5-4b-it` or your chosen quantized MedGemma 4B model.
3. Start the local server.
4. Confirm it is running at:

```text
http://127.0.0.1:1234
```

The backend automatically calls:

```text
http://127.0.0.1:1234/v1/chat/completions
```

## Neo4j Aura Setup

Create or use a Neo4j Aura instance, then place the URI, username, and password in `.env`.

When a review runs with `GRAPH_PROVIDER=neo4j`, the backend:

1. Builds graph nodes from the case schema.
2. Uses MedGemma to extract semantic clinical edges in live mode.
3. Validates those edges.
4. Writes the graph into Neo4j.
5. Retrieves evidence relationships with Cypher.

Useful Aura query:

```cypher
MATCH p=(n:EvidenceNode)-[r]->(m:EvidenceNode)
RETURN p
LIMIT 100;
```

Clinical/review edges only:

```cypher
MATCH p=(n:EvidenceNode)-[r]->(m:EvidenceNode)
WHERE type(r) IN [
  "DOCUMENTS",
  "SUPPORTS",
  "SUPPORTS_RELATIONSHIP",
  "ACTIVELY_ASSESSES",
  "CONTRADICTS",
  "CONTRADICTS_RELATIONSHIP",
  "WEAKENS",
  "SATISFIES",
  "FAILS_TO_SATISFY"
]
RETURN p
LIMIT 100;
```

## Backend Endpoints
| `GET` | `/health` | Backend health check 
| `GET` | `/capabilities` | Shows active providers/configuration 
| `GET` | `/cases` | Lists demo claim reviews 
| `GET` | `/cases/{case_id}` | Loads one review case 
| `GET` | `/cases/{case_id}/graph` | Returns graph data for visualization 
| `POST` | `/reviews` | Runs the LangGraph review workflow 
| `POST` | `/reviews/{review_id}/decision` | Saves human reviewer action 
| `GET` | `/audit` | Lists saved audit records 
| `GET` | `/evaluation` | Runs hidden expected-vs-actual checks 


## Run Tests

Backend:

```bash
source .venv/bin/activate
python -m unittest discover backend/tests
```

Frontend build:

```bash
cd frontend
npm run build
```
