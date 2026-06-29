import unittest
from dataclasses import replace
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.graph_retrieval import PreparedGraphRetriever
from backend.app.review_workflow import ClinicalReviewWorkflow


class InvalidCitationRetriever(PreparedGraphRetriever):
    def retrieve_for_submitted_diagnosis(self, case):
        package = super().retrieve_for_submitted_diagnosis(case)
        return replace(package, supporting_evidence_ids=[*package.supporting_evidence_ids, "NOTE-MISSING"])


class ClinicalReviewWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")

    def test_supported_case_runs_through_langgraph_workflow(self) -> None:
        workflow = ClinicalReviewWorkflow(self.repository)

        result = workflow.run("case_001_relationship_supported")

        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["workflow_engine"], "langgraph")
        self.assertEqual(
            result["workflow_trace"],
            [
                "load_case",
                "retrieve_graph_evidence",
                "apply_deterministic_rules",
                "citation_validation",
            ],
        )

    def test_contradicted_case_runs_conflict_analysis_branch(self) -> None:
        workflow = ClinicalReviewWorkflow(self.repository)

        result = workflow.run("case_003_newer_contradiction")

        self.assertEqual(result["status"], "contradicted")
        self.assertIn("conflict_analysis", result["workflow_trace"])
        self.assertTrue(result["conflict_analysis"]["has_conflict"])

    def test_invalid_citations_retry_once_then_escalate(self) -> None:
        workflow = ClinicalReviewWorkflow(
            self.repository,
            graph_retriever=InvalidCitationRetriever(),
        )

        result = workflow.run("case_001_relationship_supported")

        self.assertEqual(result["status"], "requires_expert_review")
        self.assertEqual(result["rule_result"], "requires_expert_review")
        self.assertEqual(result["workflow_trace"].count("retry_invalid_citations"), 1)
        self.assertIn("escalate_to_human", result["workflow_trace"])
        self.assertFalse(result["validation"]["valid"])


if __name__ == "__main__":
    unittest.main()
