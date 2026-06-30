from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from backend.app.cases import CaseRepository
from backend.app.graph_retrieval import GraphEvidencePackage, GraphRetriever, PreparedGraphRetriever


REQUIRED_FOR_SUPPORTED = {"REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"}


@dataclass(frozen=True)
class ReviewResult:
    case_id: str
    status: str
    rule_result: str
    policy_id: str
    policy_version: str
    submitted_diagnosis: str
    supporting_evidence_ids: List[str]
    contradictory_evidence_ids: List[str]
    satisfied_requirement_ids: List[str]
    missing_requirement_ids: List[str]
    supporting_evidence: List[Dict[str, Any]]
    contradictory_evidence: List[Dict[str, Any]]
    satisfied_requirements: List[Dict[str, Any]]
    missing_requirements: List[Dict[str, Any]]
    graph_paths: List[Dict[str, Any]]
    explanation: str
    validation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "rule_result": self.rule_result,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "submitted_diagnosis": self.submitted_diagnosis,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradictory_evidence_ids": self.contradictory_evidence_ids,
            "satisfied_requirement_ids": self.satisfied_requirement_ids,
            "missing_requirement_ids": self.missing_requirement_ids,
            "supporting_evidence": self.supporting_evidence,
            "contradictory_evidence": self.contradictory_evidence,
            "satisfied_requirements": self.satisfied_requirements,
            "missing_requirements": self.missing_requirements,
            "graph_paths": self.graph_paths,
            "explanation": self.explanation,
            "validation": self.validation,
        }


class DeterministicReviewEngine:
    def __init__(self, repository: CaseRepository, graph_retriever: GraphRetriever | None = None) -> None:
        self.repository = repository
        self.graph_retriever = graph_retriever or PreparedGraphRetriever()

    def review_case(self, case_id: str) -> Dict[str, Any]:
        case = self.repository.get_public_case(case_id)
        graph_evidence = self.graph_retriever.retrieve_for_submitted_diagnosis(case)
        return self.review_loaded_case(case_id, case, graph_evidence)

    def review_loaded_case(
        self,
        case_id: str,
        case: Dict[str, Any],
        graph_evidence: GraphEvidencePackage,
    ) -> Dict[str, Any]:
        submitted_diagnosis = case["claim"]["submitted_diagnoses"][0]["label"]
        satisfied_requirement_ids = graph_evidence.satisfied_requirement_ids
        failed_requirement_ids = graph_evidence.failed_requirement_ids
        missing_requirement_ids = sorted(REQUIRED_FOR_SUPPORTED - satisfied_requirement_ids)
        supporting_evidence_ids = graph_evidence.supporting_evidence_ids
        contradictory_evidence_ids = graph_evidence.contradictory_evidence_ids
        evidence_lookup = self._build_evidence_lookup(case)
        requirement_lookup = self._build_requirement_lookup(case)

        validation = self._validate_citations(
            node_ids=graph_evidence.node_ids,
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
            policy_id=case["policy"]["id"],
            policy_version=case["policy"]["version"],
            submitted_diagnosis=submitted_diagnosis,
            supporting_evidence_ids=supporting_evidence_ids,
            contradictory_evidence_ids=contradictory_evidence_ids,
            satisfied_requirement_ids=sorted(satisfied_requirement_ids),
            missing_requirement_ids=missing_requirement_ids,
            supporting_evidence=self._resolve_items(supporting_evidence_ids, evidence_lookup),
            contradictory_evidence=self._resolve_items(contradictory_evidence_ids, evidence_lookup),
            satisfied_requirements=self._resolve_items(sorted(satisfied_requirement_ids), requirement_lookup),
            missing_requirements=self._resolve_items(missing_requirement_ids, requirement_lookup),
            graph_paths=graph_evidence.graph_paths,
            explanation=explanation,
            validation=validation,
        )
        return result.to_dict()

    @staticmethod
    def _build_evidence_lookup(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        evidence: Dict[str, Dict[str, Any]] = {}

        for note in case["notes"]["notes"]:
            evidence[note["id"]] = {
                "id": note["id"],
                "kind": "note",
                "title": note["type"],
                "date": note["date"],
                "page": note["page"],
                "section": note["section"],
                "text": note["text"],
                "encounter_id": note["encounter_id"],
            }

        for lab in case["labs"]["labs"]:
            evidence[lab["id"]] = {
                "id": lab["id"],
                "kind": "lab",
                "title": lab["test"],
                "date": lab["date"],
                "value": lab["value"],
                "unit": lab["unit"],
                "interpretation": lab["interpretation"],
                "encounter_id": lab["encounter_id"],
            }

        return evidence

    @staticmethod
    def _build_requirement_lookup(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        return {
            requirement["id"]: {
                "id": requirement["id"],
                "label": requirement["label"],
                "description": requirement["description"],
            }
            for requirement in case["policy"]["requirements"]
        }

    @staticmethod
    def _resolve_items(item_ids: List[str], lookup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [lookup[item_id] for item_id in item_ids if item_id in lookup]

    @staticmethod
    def _validate_citations(node_ids: Set[str], evidence_ids: List[str], requirement_ids: List[str]) -> Dict[str, Any]:
        missing_evidence_ids = sorted(evidence_id for evidence_id in evidence_ids if evidence_id not in node_ids)
        missing_requirement_ids = sorted(requirement_id for requirement_id in requirement_ids if requirement_id not in node_ids)
        return {
            "valid": not missing_evidence_ids and not missing_requirement_ids,
            "missing_evidence_ids": missing_evidence_ids,
            "missing_requirement_ids": missing_requirement_ids,
        }
