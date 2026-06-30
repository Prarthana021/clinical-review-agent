import unittest

from backend.app.model_explanations import (
    CachedExplanationAdapter,
    LocalHTTPExplanationAdapter,
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

    def test_factory_builds_local_http_adapter(self) -> None:
        adapter = build_explanation_adapter(
            AppSettings(
                model_provider="local_http",
                local_llm_base_url="http://127.0.0.1:1234/v1",
                local_llm_model="medgemma-4b-it-mlx",
            )
        )

        self.assertIsInstance(adapter, LocalHTTPExplanationAdapter)

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

    def test_local_http_adapter_parses_openai_compatible_response(self) -> None:
        adapter = LocalHTTPExplanationAdapter(
            base_url="http://127.0.0.1:1234/v1",
            model_name="medgemma-4b-it-mlx",
        )
        adapter._chat_completion = lambda prompt: (
            '{"status": "supported", "explanation": "Evidence supports the deterministic result."}'
        )
        review_result = {
            "status": "supported",
            "explanation": "Base explanation.",
            "submitted_diagnosis": "Type 2 diabetes mellitus with CKD stage 3",
            "supporting_evidence_ids": ["NOTE-001"],
            "semantic_evidence_ids": ["NOTE-001"],
            "contradictory_evidence_ids": [],
            "missing_requirement_ids": [],
            "missing_requirements": [],
        }

        explanation = adapter.explain(review_result)

        self.assertEqual(explanation.mode, "local_http_medgemma")
        self.assertEqual(explanation.proposed_status, "supported")
        self.assertEqual(explanation.explanation, "Evidence supports the deterministic result.")

    def test_local_http_adapter_falls_back_when_server_is_unavailable(self) -> None:
        adapter = LocalHTTPExplanationAdapter(
            base_url="http://127.0.0.1:1234/v1",
            model_name="medgemma-4b-it-mlx",
        )
        adapter._chat_completion = lambda prompt: (_ for _ in ()).throw(RuntimeError("server unavailable"))
        review_result = {
            "status": "supported",
            "explanation": "Base explanation.",
            "submitted_diagnosis": "Type 2 diabetes mellitus with CKD stage 3",
            "supporting_evidence_ids": ["NOTE-001"],
            "semantic_evidence_ids": ["NOTE-001"],
            "contradictory_evidence_ids": [],
            "missing_requirement_ids": [],
            "missing_requirements": [],
        }

        explanation = adapter.explain(review_result)

        self.assertEqual(explanation.mode, "cached_fallback_after_local_http_error")


if __name__ == "__main__":
    unittest.main()
