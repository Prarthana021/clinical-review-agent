import unittest

from backend.app.capabilities import build_capabilities
from backend.app.settings import AppSettings


class CapabilityReportTests(unittest.TestCase):
    def test_capabilities_report_core_project_integrations(self) -> None:
        capabilities = build_capabilities(
            AppSettings(
                graph_provider="prepared_json",
                vector_provider="chromadb",
                model_provider="medgemma",
                medgemma_model_id="google/medgemma-1.5-4b-it",
            )
        )

        self.assertEqual(capabilities["workflow"]["engine"], "langgraph")
        self.assertTrue(capabilities["graph"]["prepared_json_fallback"])
        self.assertEqual(capabilities["graph"]["relation_extractor"], "deterministic_extraction")
        self.assertTrue(capabilities["vector"]["chromadb_configured"])
        self.assertEqual(capabilities["vector"]["purpose"], "semantic_note_and_lab_retrieval")
        self.assertTrue(capabilities["model"]["live_medgemma_configured"])
        self.assertEqual(capabilities["model"]["decision_authority"], "deterministic_graph_policy_rules")
        self.assertTrue(capabilities["audit"]["stores_policy_version"])
        self.assertTrue(capabilities["data"]["synthetic_only"])

    def test_capabilities_report_medgemma_relation_extraction_for_local_http_model(self) -> None:
        capabilities = build_capabilities(
            AppSettings(
                graph_provider="neo4j",
                model_provider="local_http",
                relation_extractor_provider="auto",
            )
        )

        self.assertEqual(capabilities["graph"]["relation_extractor"], "medgemma_semantic_extraction")


if __name__ == "__main__":
    unittest.main()
