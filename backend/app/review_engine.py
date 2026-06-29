from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from backend.app.cases import CaseRepository


REQUIRED_FOR_SUPPORTED = {"REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"}


@dataclass(frozen=True)
class ReviewResult:
    case_id: str
    status: str
    rule_result: str
    submitted_diagnosis: str
    supporting_evidence_ids: List[str]
    contradictory_evidence_ids: List[str]
    satisfied_requirement_ids: List[str]
    missing_requirement_ids: List[str]
    graph_paths: List[Dict[str, Any]]
    explanation: str
    validation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "rule_result": self.rule_result,
            "submitted_diagnosis": self.submitted_diagnosis,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradictory_evidence_ids": self.contradictory_evidence_ids,
            "satisfied_requirement_ids": self.satisfied_requirement_ids,
            "missing_requirement_ids": self.missing_requirement_ids,
            "graph_paths": self.graph_paths,
            "explanation": self.explanation,
            "validation": self.validation,
        }


class DeterministicReviewEngine:
    def __init__(self, repository: CaseRepository) -> None:
        self.repository = repository

    def review_case(self, case_id: str) -> Dict[str, Any]:
        case = self.repository.get_public_case(case_id)
        graph = case["graph"]
        relationships = graph["relationships"]
        node_ids = {node["id"] for node in graph["nodes"]}

        submitted_diagnosis = case["claim"]["submitted_diagnoses"][0]["label"]
        satisfied_requirement_ids = self._requirement_ids_for_relationships(relationships, "SATISFIES")
        failed_requirement_ids = self._requirement_ids_for_relationships(relationships, "FAILS_TO_SATISFY")
        missing_requirement_ids = sorted(REQUIRED_FOR_SUPPORTED - satisfied_requirement_ids)
        supporting_evidence_ids = self._supporting_evidence_ids(relationships)
        contradictory_evidence_ids = self._contradictory_evidence_ids(relationships)

        validation = self._validate_citations(
            node_ids=node_ids,
            evidence_ids=supporting_evidence_ids + contradictory_evidence_ids,
            requirement_ids=sorted(satisfied_requirement_ids | set(missing_requirement_ids) | failed_requirement_ids),
        )

        if not validation["valid"]:
            status = "insufficient_evidence"
            explanation = "The review result contains invalid citations, so the case cannot be classified from the available evidence."
        elif contradictory_evidence_ids:
            status = "contradicted"
            explanation = "Newer or conflicting evidence contradicts the submitted diagnosis or its required condition relationship."
        elif REQUIRED_FOR_SUPPORTED.issubset(satisfied_requirement_ids):
            status = "supported"
            explanation = "The graph contains current documentation, relationship evidence, and assessment or management evidence required by the synthetic policy."
        elif not supporting_evidence_ids:
            status = "unsupported"
            explanation = "The graph did not retrieve evidence supporting the submitted diagnosis."
        else:
            status = "insufficient_evidence"
            explanation = "The graph retrieved some supporting evidence, but required policy evidence is missing."

        result = ReviewResult(
            case_id=case_id,
            status=status,
            rule_result=status,
            submitted_diagnosis=submitted_diagnosis,
            supporting_evidence_ids=supporting_evidence_ids,
            contradictory_evidence_ids=contradictory_evidence_ids,
            satisfied_requirement_ids=sorted(satisfied_requirement_ids),
            missing_requirement_ids=missing_requirement_ids,
            graph_paths=self._graph_paths(relationships),
            explanation=explanation,
            validation=validation,
        )
        return result.to_dict()

    @staticmethod
    def _requirement_ids_for_relationships(relationships: List[Dict[str, str]], relationship_type: str) -> Set[str]:
        return {rel["target"] for rel in relationships if rel["type"] == relationship_type and rel["target"].startswith("REQ-")}

    @staticmethod
    def _supporting_evidence_ids(relationships: List[Dict[str, str]]) -> List[str]:
        support_types = {"DOCUMENTS", "SUPPORTS", "SUPPORTS_RELATIONSHIP", "ACTIVELY_ASSESSES"}
        evidence_ids = {
            rel["source"]
            for rel in relationships
            if rel["type"] in support_types and (rel["source"].startswith("NOTE-") or rel["source"].startswith("LAB-"))
        }
        return sorted(evidence_ids)

    @staticmethod
    def _contradictory_evidence_ids(relationships: List[Dict[str, str]]) -> List[str]:
        contradiction_types = {"CONTRADICTS", "CONTRADICTS_RELATIONSHIP", "SUPERSEDES", "WEAKENS"}
        evidence_ids = {
            rel["source"]
            for rel in relationships
            if rel["type"] in contradiction_types and (rel["source"].startswith("NOTE-") or rel["source"].startswith("LAB-"))
        }
        return sorted(evidence_ids)

    @staticmethod
    def _graph_paths(relationships: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        important_types = {
            "SUBMITS",
            "REQUIRES_RELATIONSHIP",
            "SUPPORTS_RELATIONSHIP",
            "CONTRADICTS",
            "CONTRADICTS_RELATIONSHIP",
            "SUPERSEDES",
            "WEAKENS",
            "SATISFIES",
        }
        return [
            {
                "source": rel["source"],
                "relationship": rel["type"],
                "target": rel["target"],
            }
            for rel in relationships
            if rel["type"] in important_types
        ]

    @staticmethod
    def _validate_citations(node_ids: Set[str], evidence_ids: List[str], requirement_ids: List[str]) -> Dict[str, Any]:
        missing_evidence_ids = sorted(evidence_id for evidence_id in evidence_ids if evidence_id not in node_ids)
        missing_requirement_ids = sorted(requirement_id for requirement_id in requirement_ids if requirement_id not in node_ids)
        return {
            "valid": not missing_evidence_ids and not missing_requirement_ids,
            "missing_evidence_ids": missing_evidence_ids,
            "missing_requirement_ids": missing_requirement_ids,
        }
