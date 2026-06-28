import unittest
from pathlib import Path

from backend.app.cases import CaseRepository


class CaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")

    def test_list_cases_returns_three_cases(self) -> None:
        cases = self.repository.list_cases()

        self.assertEqual(len(cases), 3)
        self.assertEqual(
            [case["id"] for case in cases],
            [
                "case_001_relationship_supported",
                "case_002_insufficient_evidence",
                "case_003_newer_contradiction",
            ],
        )

    def test_public_case_excludes_expected_result(self) -> None:
        case = self.repository.get_public_case("case_001_relationship_supported")

        self.assertIn("patient", case)
        self.assertIn("claim", case)
        self.assertIn("graph", case)
        self.assertNotIn("expected_result", case)

    def test_each_public_case_loads_required_sections(self) -> None:
        for case_summary in self.repository.list_cases():
            with self.subTest(case_id=case_summary["id"]):
                case = self.repository.get_public_case(case_summary["id"])

                self.assertIn("patient", case)
                self.assertIn("claim", case)
                self.assertIn("conditions", case)
                self.assertIn("encounters", case)
                self.assertIn("notes", case)
                self.assertIn("labs", case)
                self.assertIn("policy", case)
                self.assertIn("graph", case)

    def test_expected_results_are_available_for_internal_evaluation(self) -> None:
        expected = {
            "case_001_relationship_supported": "supported",
            "case_002_insufficient_evidence": "insufficient_evidence",
            "case_003_newer_contradiction": "contradicted",
        }

        for case_id, expected_status in expected.items():
            with self.subTest(case_id=case_id):
                result = self.repository.get_expected_result(case_id)
                self.assertEqual(result["expected_status"], expected_status)


if __name__ == "__main__":
    unittest.main()

