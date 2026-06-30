from __future__ import annotations

import importlib.util
from typing import Any, Dict

from backend.app.settings import AppSettings


def build_capabilities(settings: AppSettings) -> Dict[str, Any]:
    medgemma_dependencies_available = all(
        importlib.util.find_spec(package_name) is not None
        for package_name in ("transformers", "accelerate", "torch")
    )
    medgemma_configured = settings.model_provider == "medgemma"
    chromadb_available = importlib.util.find_spec("chromadb") is not None

    return {
        "workflow": {
            "engine": "langgraph",
            "conditional_paths": [
                "missing_evidence_search_again",
                "contradiction_conflict_analysis",
                "invalid_citations_retry_once",
                "unresolved_escalate_to_human",
            ],
        },
        "graph": {
            "provider": settings.graph_provider,
            "live_neo4j": settings.graph_provider == "neo4j",
            "prepared_json_fallback": settings.graph_provider == "prepared_json",
        },
        "vector": {
            "provider": settings.vector_provider,
            "chromadb_configured": settings.vector_provider == "chromadb",
            "chromadb_available": chromadb_available,
            "embedding_mode": "local_hash_embeddings",
            "purpose": "semantic_note_and_lab_retrieval",
        },
        "model": {
            "provider": settings.model_provider,
            "medgemma_model_id": settings.medgemma_model_id,
            "live_medgemma_configured": medgemma_configured,
            "medgemma_dependencies_available": medgemma_dependencies_available,
            "cached_fallback_enabled": True,
            "decision_authority": "deterministic_graph_policy_rules",
            "model_role": "reviewer_facing_explanation",
        },
        "audit": {
            "stores_policy_version": True,
            "stores_model_metadata": True,
            "stores_evidence_ids": True,
            "stores_graph_paths": True,
            "stores_validation_result": True,
            "stores_human_decision": True,
        },
        "data": {
            "synthetic_only": True,
            "real_patient_data": False,
        },
    }
