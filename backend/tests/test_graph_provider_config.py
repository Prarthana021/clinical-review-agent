import unittest
from unittest.mock import patch

from backend.app.graph_retrieval import (
    GraphConfigurationError,
    Neo4jGraphRetriever,
    PreparedGraphRetriever,
    build_graph_retriever,
)
from backend.app.settings import AppSettings, load_settings


class GraphProviderConfigTests(unittest.TestCase):
    def test_default_settings_use_prepared_json_provider(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = load_settings()

        retriever = build_graph_retriever(settings)

        self.assertEqual(settings.graph_provider, "prepared_json")
        self.assertIsInstance(retriever, PreparedGraphRetriever)

    def test_neo4j_provider_requires_connection_settings(self) -> None:
        settings = AppSettings(graph_provider="neo4j")

        with self.assertRaises(GraphConfigurationError):
            build_graph_retriever(settings)

    def test_neo4j_provider_can_be_constructed_when_configured(self) -> None:
        settings = AppSettings(
            graph_provider="neo4j",
            neo4j_uri="neo4j://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )

        retriever = build_graph_retriever(settings)

        self.assertIsInstance(retriever, Neo4jGraphRetriever)
        retriever.close()

    def test_unsupported_provider_fails_clearly(self) -> None:
        settings = AppSettings(graph_provider="unknown")

        with self.assertRaises(GraphConfigurationError):
            build_graph_retriever(settings)


if __name__ == "__main__":
    unittest.main()
