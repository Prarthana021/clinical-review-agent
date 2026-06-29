import tempfile
import unittest
from pathlib import Path

from backend.app.audit import AuditRepository, InvalidReviewerActionError, ReviewNotFoundError


class AuditRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit = AuditRepository(Path(self.temp_dir.name) / "audit.sqlite3")
        self.review_result = {
            "case_id": "case_001_relationship_supported",
            "status": "supported",
            "rule_result": "supported",
            "submitted_diagnosis": "Type 2 diabetes mellitus with chronic kidney disease stage 3",
            "supporting_evidence_ids": ["NOTE-001", "LAB-001"],
            "contradictory_evidence_ids": [],
            "satisfied_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"],
            "missing_requirement_ids": [],
            "graph_paths": [{"source": "NOTE-001", "relationship": "SATISFIES", "target": "REQ-003"}],
            "explanation": "Synthetic explanation.",
            "model": {"model_name": "cached-medgemma-placeholder", "mode": "cached_fallback"},
            "validation": {"valid": True, "missing_evidence_ids": [], "missing_requirement_ids": []},
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_review_result_is_persisted_with_review_id(self) -> None:
        saved = self.audit.save_review_result(self.review_result)

        self.assertIn("review_id", saved)
        loaded = self.audit.get_review_result(saved["review_id"])
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["case_id"], "case_001_relationship_supported")
        self.assertEqual(loaded["status"], "supported")

    def test_reviewer_decision_creates_audit_record(self) -> None:
        saved = self.audit.save_review_result(self.review_result)

        audit_record = self.audit.save_reviewer_decision(
            review_id=saved["review_id"],
            action="approve",
            comment="Evidence supports the submitted diagnosis.",
            reviewer_id="reviewer-1",
        )

        self.assertIn("audit_id", audit_record)
        self.assertEqual(audit_record["review_id"], saved["review_id"])
        self.assertEqual(audit_record["ai_status"], "supported")
        self.assertEqual(audit_record["reviewer_action"], "approve")
        self.assertEqual(audit_record["supporting_evidence_ids"], ["NOTE-001", "LAB-001"])
        self.assertEqual(audit_record["model"]["mode"], "cached_fallback")

    def test_audit_records_are_listed(self) -> None:
        saved = self.audit.save_review_result(self.review_result)
        self.audit.save_reviewer_decision(saved["review_id"], "request_documentation", "Need more detail.")

        records = self.audit.list_audit_records()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["reviewer_action"], "request_documentation")

    def test_unknown_review_id_fails_decision_save(self) -> None:
        with self.assertRaises(ReviewNotFoundError):
            self.audit.save_reviewer_decision("missing-review", "approve")

    def test_invalid_reviewer_action_fails_decision_save(self) -> None:
        saved = self.audit.save_review_result(self.review_result)

        with self.assertRaises(InvalidReviewerActionError):
            self.audit.save_reviewer_decision(saved["review_id"], "maybe")


if __name__ == "__main__":
    unittest.main()
