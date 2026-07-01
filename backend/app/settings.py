from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    graph_provider: str = "prepared_json"
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    vector_provider: str = "chromadb"
    model_provider: str = "cached"
    medgemma_model_id: str = "google/medgemma-1.5-4b-it"
    huggingface_token: str | None = None
    local_llm_base_url: str = "http://127.0.0.1:1234"
    local_llm_model: str = "medgemma-1.5-4b-it"
    relation_extractor_provider: str = "auto"


def load_settings() -> AppSettings:
    _load_dotenv()
    return AppSettings(
        graph_provider=os.getenv("GRAPH_PROVIDER", "prepared_json"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        vector_provider=os.getenv("VECTOR_PROVIDER", "chromadb"),
        model_provider=os.getenv("MODEL_PROVIDER", "cached"),
        medgemma_model_id=os.getenv("MEDGEMMA_MODEL_ID", "google/medgemma-1.5-4b-it"),
        huggingface_token=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN"),
        local_llm_base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234"),
        local_llm_model=os.getenv("LOCAL_LLM_MODEL") or os.getenv("LM_STUDIO_MODEL", "medgemma-1.5-4b-it"),
        relation_extractor_provider=os.getenv("RELATION_EXTRACTOR_PROVIDER", "auto"),
    )


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
