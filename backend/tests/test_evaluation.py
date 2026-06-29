import unittest
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.evaluation import EvaluationRunner
from backend.app.review_workflow import ClinicalReviewWorkflow


class EvaluationRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")
        self.runner = EvaluationRunner(self.repository, ClinicalReviewWorkflow(self.repository))

    def test_all_cases_pass_expected_results(self) -> None:
        evaluation = self.runner.run_all_cases()

        self.assertEqual(evaluation["total_cases"], 3)
        self.assertEqual(evaluation["passed_cases"], 3)
        self.assertEqual(evaluation["failed_cases"], 0)
        self.assertTrue(all(case["passed"] for case in evaluation["cases"]))

    def test_evaluation_reports_expected_and_actual_status(self) -> None:
        evaluation = self.runner.run_all_cases()
        case_by_id = {case["case_id"]: case for case in evaluation["cases"]}

        supported = case_by_id["case_001_relationship_supported"]
        self.assertEqual(supported["expected_status"], "supported")
        self.assertEqual(supported["actual_status"], "supported")
        self.assertTrue(supported["citations_valid"])
        self.assertTrue(supported["graph_paths_present"])


if __name__ == "__main__":
    unittest.main()
