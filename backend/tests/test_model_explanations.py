import unittest

from backend.app.model_explanations import CachedExplanationAdapter


class CachedExplanationAdapterTests(unittest.TestCase):
    def test_explanation_preserves_status_context_and_lists_missing_requirements(self) -> None:
        adapter = CachedExplanationAdapter()
        review_result = {
            "status": "insufficient_evidence",
            "explanation": "Base explanation.",
            "missing_requirements": [{"label": "Relationship evidence"}],
            "contradictory_evidence_ids": [],
        }

        explanation = adapter.explain(review_result)

        self.assertEqual(explanation.mode, "cached_fallback")
        self.assertEqual(explanation.model_name, "cached-medgemma-placeholder")
        self.assertIn("Missing requirements: Relationship evidence", explanation.explanation)


if __name__ == "__main__":
    unittest.main()
