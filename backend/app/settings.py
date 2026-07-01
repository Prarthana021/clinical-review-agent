from __future__ import annotations

import os
from dataclasses import dataclass


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


def load_settings() -> AppSettings:
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
    )
