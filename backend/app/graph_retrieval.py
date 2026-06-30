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
    semantic_evidence_ids: List[str]
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
            semantic_evidence_ids=[],
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
    """Neo4j-backed graph retrieval.

    The POC still uses validated synthetic cases as source data. In Neo4j mode,
    this retriever upserts the case graph into Neo4j, then retrieves the
    relationship-aware evidence package with Cypher queries.
    """

    def __init__(self, uri: str | None, user: str | None, password: str | None) -> None:
        if not uri or not user or not password:
            raise GraphConfigurationError(
                "Neo4j graph provider requires NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
            )
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise GraphConfigurationError("GRAPH_PROVIDER=neo4j requires the neo4j Python package.") from exc

        self.uri = uri
        self.user = user
        self.password = password
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def retrieve_for_submitted_diagnosis(self, case: Dict[str, Any]) -> GraphEvidencePackage:
        self._upsert_case_graph(case)
        relationships = self._relationships_for_case(case["id"])
        node_ids = self._node_ids_for_case(case["id"])

        return GraphEvidencePackage(
            node_ids=node_ids,
            supporting_evidence_ids=PreparedGraphRetriever._evidence_ids_for_relationships(
                relationships,
                SUPPORT_RELATIONSHIP_TYPES,
            ),
            contradictory_evidence_ids=PreparedGraphRetriever._evidence_ids_for_relationships(
                relationships,
                CONTRADICTION_RELATIONSHIP_TYPES,
            ),
            semantic_evidence_ids=[],
            satisfied_requirement_ids=PreparedGraphRetriever._requirement_ids_for_relationships(
                relationships,
                "SATISFIES",
            ),
            failed_requirement_ids=PreparedGraphRetriever._requirement_ids_for_relationships(
                relationships,
                "FAILS_TO_SATISFY",
            ),
            graph_paths=PreparedGraphRetriever._graph_paths(relationships),
        )

    def close(self) -> None:
        self._driver.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _upsert_case_graph(self, case: Dict[str, Any]) -> None:
        graph = case["graph"]
        with self._driver.session() as session:
            for node in graph["nodes"]:
                session.execute_write(self._merge_node, case["id"], node)
            for relationship in graph["relationships"]:
                session.execute_write(self._merge_relationship, case["id"], relationship)

    @staticmethod
    def _merge_node(tx, case_id: str, node: Dict[str, str]) -> None:
        tx.run(
            """
            MERGE (n:EvidenceNode {uid: $uid})
            SET n.id = $id,
                n.case_id = $case_id,
                n.type = $type,
                n.label = $label
            """,
            uid=f"{case_id}:{node['id']}",
            id=node["id"],
            case_id=case_id,
            type=node["type"],
            label=node["label"],
        )

    @staticmethod
    def _merge_relationship(tx, case_id: str, relationship: Dict[str, str]) -> None:
        relationship_type = Neo4jGraphRetriever._safe_relationship_type(relationship["type"])
        tx.run(
            f"""
            MATCH (source:EvidenceNode {{uid: $source_uid}})
            MATCH (target:EvidenceNode {{uid: $target_uid}})
            MERGE (source)-[r:`{relationship_type}`]->(target)
            SET r.type = $type,
                r.case_id = $case_id
            """,
            source_uid=f"{case_id}:{relationship['source']}",
            target_uid=f"{case_id}:{relationship['target']}",
            type=relationship["type"],
            case_id=case_id,
        )

    def _relationships_for_case(self, case_id: str) -> List[Dict[str, str]]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (source:EvidenceNode {case_id: $case_id})-[relationship]->(target:EvidenceNode {case_id: $case_id})
                RETURN source.id AS source,
                       relationship.type AS type,
                       target.id AS target
                """,
                case_id=case_id,
            )
            return [
                {
                    "source": row["source"],
                    "type": row["type"],
                    "target": row["target"],
                }
                for row in rows
            ]

    def _node_ids_for_case(self, case_id: str) -> Set[str]:
        with self._driver.session() as session:
            rows = session.run(
                """
                MATCH (node:EvidenceNode {case_id: $case_id})
                RETURN node.id AS id
                """,
                case_id=case_id,
            )
            return {row["id"] for row in rows}

    @staticmethod
    def _safe_relationship_type(value: str) -> str:
        if not value.replace("_", "").isalnum():
            raise GraphConfigurationError(f"Unsafe Neo4j relationship type: {value}")
        return value


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
