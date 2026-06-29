import unittest
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.review_engine import DeterministicReviewEngine


class DeterministicReviewEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        repository = CaseRepository(repo_root / "data")
        self.repository = repository
        self.engine = DeterministicReviewEngine(repository)

    def test_review_status_matches_expected_result_for_all_cases(self) -> None:
        for case_summary in self.repository.list_cases():
            case_id = case_summary["id"]
            with self.subTest(case_id=case_id):
                review = self.engine.review_case(case_id)
                expected = self.repository.get_expected_result(case_id)

                self.assertEqual(review["status"], expected["expected_status"])

    def test_review_result_has_valid_citations(self) -> None:
        for case_summary in self.repository.list_cases():
            case_id = case_summary["id"]
            with self.subTest(case_id=case_id):
                review = self.engine.review_case(case_id)

                self.assertTrue(review["validation"]["valid"])
                self.assertEqual(review["validation"]["missing_evidence_ids"], [])
                self.assertEqual(review["validation"]["missing_requirement_ids"], [])

    def test_supported_case_has_relationship_evidence(self) -> None:
        review = self.engine.review_case("case_001_relationship_supported")

        self.assertEqual(review["status"], "supported")
        self.assertIn("NOTE-001", review["supporting_evidence_ids"])
        self.assertIn("REQ-003", review["satisfied_requirement_ids"])

    def test_insufficient_case_does_not_become_supported_from_separate_conditions(self) -> None:
        review = self.engine.review_case("case_002_insufficient_evidence")

        self.assertEqual(review["status"], "insufficient_evidence")
        self.assertIn("REQ-003", review["missing_requirement_ids"])
        self.assertIn("REQ-005", review["missing_requirement_ids"])

    def test_contradicted_case_reports_contradictory_evidence(self) -> None:
        review = self.engine.review_case("case_003_newer_contradiction")

        self.assertEqual(review["status"], "contradicted")
        self.assertEqual(review["contradictory_evidence_ids"], ["LAB-011", "LAB-012", "NOTE-005", "NOTE-023"])


if __name__ == "__main__":
    unittest.main()
