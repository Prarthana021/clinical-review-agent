import unittest

from backend.app.model_explanations import (
    CachedExplanationAdapter,
    MedGemmaExplanationAdapter,
    ModelConfigurationError,
    build_explanation_adapter,
)
from backend.app.settings import AppSettings


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

    def test_factory_defaults_to_cached_provider(self) -> None:
        adapter = build_explanation_adapter(AppSettings(model_provider="cached"))

        self.assertIsInstance(adapter, CachedExplanationAdapter)

    def test_factory_builds_medgemma_adapter_without_loading_model(self) -> None:
        adapter = build_explanation_adapter(
            AppSettings(
                model_provider="medgemma",
                medgemma_model_id="google/medgemma-1.5-4b-it",
            )
        )

        self.assertIsInstance(adapter, MedGemmaExplanationAdapter)

    def test_unsupported_model_provider_fails_clearly(self) -> None:
        with self.assertRaises(ModelConfigurationError):
            build_explanation_adapter(AppSettings(model_provider="unknown"))

    def test_medgemma_adapter_falls_back_when_runtime_is_unavailable(self) -> None:
        adapter = MedGemmaExplanationAdapter("google/medgemma-1.5-4b-it")
        adapter._load_pipeline = lambda: (_ for _ in ()).throw(RuntimeError("model unavailable"))
        review_result = {
            "status": "supported",
            "explanation": "Base explanation.",
            "submitted_diagnosis": "Type 2 diabetes mellitus with CKD stage 3",
            "supporting_evidence_ids": ["NOTE-001"],
            "contradictory_evidence_ids": [],
            "missing_requirement_ids": [],
            "missing_requirements": [],
        }

        explanation = adapter.explain(review_result)

        self.assertEqual(explanation.model_name, "google/medgemma-1.5-4b-it")
        self.assertEqual(explanation.mode, "cached_fallback_after_medgemma_error")


if __name__ == "__main__":
    unittest.main()
