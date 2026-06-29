from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Set

from backend.app.settings import AppSettings


SUPPORT_RELATIONSHIP_TYPES = {"DOCUMENTS", "SUPPORTS", "SUPPORTS_RELATIONSHIP", "ACTIVELY_ASSESSES"}
CONTRADICTION_RELATIONSHIP_TYPES = {"CONTRADICTS", "CONTRADICTS_RELATIONSHIP", "SUPERSEDES", "WEAKENS"}
IMPORTANT_PATH_TYPES = {
    "SUBMITS",
    "REQUIRES_RELATIONSHIP",
    "SUPPORTS_RELATIONSHIP",
    "CONTRADICTS",
    "CONTRADICTS_RELATIONSHIP",
    "SUPERSEDES",
    "WEAKENS",
    "SATISFIES",
}


@dataclass(frozen=True)
class GraphEvidencePackage:
    node_ids: Set[str]
    supporting_evidence_ids: List[str]
    contradictory_evidence_ids: List[str]
    satisfied_requirement_ids: Set[str]
    failed_requirement_ids: Set[str]
    graph_paths: List[Dict[str, Any]]


class GraphRetriever(Protocol):
    def retrieve_for_submitted_diagnosis(self, case: Dict[str, Any]) -> GraphEvidencePackage:
        ...


class GraphConfigurationError(Exception):
    """Raised when the selected graph provider cannot be configured."""


class PreparedGraphRetriever:
    """Retrieves relationship-aware evidence from the prepared case graph.

    The MVP stores graph data in JSON for reliability. This class is the boundary
    that later lets us replace JSON traversal with Neo4j/Cypher retrieval.
    """

    def retrieve_for_submitted_diagnosis(self, case: Dict[str, Any]) -> GraphEvidencePackage:
        graph = case["graph"]
        relationships = graph["relationships"]

        return GraphEvidencePackage(
            node_ids={node["id"] for node in graph["nodes"]},
            supporting_evidence_ids=self._evidence_ids_for_relationships(
                relationships,
                SUPPORT_RELATIONSHIP_TYPES,
            ),
            contradictory_evidence_ids=self._evidence_ids_for_relationships(
                relationships,
                CONTRADICTION_RELATIONSHIP_TYPES,
            ),
            satisfied_requirement_ids=self._requirement_ids_for_relationships(relationships, "SATISFIES"),
            failed_requirement_ids=self._requirement_ids_for_relationships(relationships, "FAILS_TO_SATISFY"),
            graph_paths=self._graph_paths(relationships),
        )

    @staticmethod
    def _requirement_ids_for_relationships(relationships: List[Dict[str, str]], relationship_type: str) -> Set[str]:
        return {
            rel["target"]
            for rel in relationships
            if rel["type"] == relationship_type and rel["target"].startswith("REQ-")
        }

    @staticmethod
    def _evidence_ids_for_relationships(
        relationships: List[Dict[str, str]],
        relationship_types: Set[str],
    ) -> List[str]:
        evidence_ids = {
            rel["source"]
            for rel in relationships
            if rel["type"] in relationship_types
            and (rel["source"].startswith("NOTE-") or rel["source"].startswith("LAB-"))
        }
        return sorted(evidence_ids)

    @staticmethod
    def _graph_paths(relationships: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        return [
            {
                "source": rel["source"],
                "relationship": rel["type"],
                "target": rel["target"],
            }
            for rel in relationships
            if rel["type"] in IMPORTANT_PATH_TYPES
        ]


class Neo4jGraphRetriever:
    """Neo4j provider boundary for the future Cypher implementation."""

    def __init__(self, uri: str | None, user: str | None, password: str | None) -> None:
        if not uri or not user or not password:
            raise GraphConfigurationError(
                "Neo4j graph provider requires NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
            )
        self.uri = uri
        self.user = user
        self.password = password

    def retrieve_for_submitted_diagnosis(self, case: Dict[str, Any]) -> GraphEvidencePackage:
        raise GraphConfigurationError(
            "Neo4j graph retrieval is configured but not implemented for the MVP. "
            "Use GRAPH_PROVIDER=prepared_json for the local demo."
        )


def build_graph_retriever(settings: AppSettings) -> GraphRetriever:
    if settings.graph_provider == "prepared_json":
        return PreparedGraphRetriever()
    if settings.graph_provider == "neo4j":
        return Neo4jGraphRetriever(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    raise GraphConfigurationError(f"Unsupported graph provider: {settings.graph_provider}")
