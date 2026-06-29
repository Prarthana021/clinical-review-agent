from __future__ import annotations

from typing import Any, Dict

from backend.app.cases import CaseRepository
from backend.app.review_workflow import ClinicalReviewWorkflow


class EvaluationRunner:
    def __init__(self, repository: CaseRepository, workflow: ClinicalReviewWorkflow) -> None:
        self.repository = repository
        self.workflow = workflow

    def run_all_cases(self) -> Dict[str, Any]:
        case_results = [self._evaluate_case(case_summary["id"]) for case_summary in self.repository.list_cases()]
        passed_count = sum(1 for result in case_results if result["passed"])

        return {
            "total_cases": len(case_results),
            "passed_cases": passed_count,
            "failed_cases": len(case_results) - passed_count,
            "cases": case_results,
        }

    def _evaluate_case(self, case_id: str) -> Dict[str, Any]:
        expected = self.repository.get_expected_result(case_id)
        actual = self.workflow.run(case_id)

        expected_supporting_ids = set(expected["supporting_evidence_ids"])
        actual_supporting_ids = set(actual["supporting_evidence_ids"])
        expected_contradictory_ids = set(expected["contradictory_evidence_ids"])
        actual_contradictory_ids = set(actual["contradictory_evidence_ids"])

        status_matches = actual["status"] == expected["expected_status"]
        citations_valid = actual["validation"]["valid"]
        supporting_recall = expected_supporting_ids.issubset(actual_supporting_ids)
        contradiction_recall = expected_contradictory_ids.issubset(actual_contradictory_ids)
        graph_paths_present = len(actual["graph_paths"]) > 0
        passed = (
            status_matches
            and citations_valid
            and supporting_recall
            and contradiction_recall
            and graph_paths_present
        )

        return {
            "case_id": case_id,
            "expected_status": expected["expected_status"],
            "actual_status": actual["status"],
            "passed": passed,
            "status_matches": status_matches,
            "citations_valid": citations_valid,
            "supporting_evidence_recall": supporting_recall,
            "contradictory_evidence_recall": contradiction_recall,
            "graph_paths_present": graph_paths_present,
            "expected_supporting_evidence_ids": expected["supporting_evidence_ids"],
            "actual_supporting_evidence_ids": actual["supporting_evidence_ids"],
            "expected_contradictory_evidence_ids": expected["contradictory_evidence_ids"],
            "actual_contradictory_evidence_ids": actual["contradictory_evidence_ids"],
            "workflow_trace": actual.get("workflow_trace", []),
        }
