import unittest
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.graph_view import DISPLAY_RELATIONSHIP_TYPES, build_graph_view


class GraphViewTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")

    def test_graph_view_filters_to_display_relationships(self) -> None:
        case = self.repository.get_public_case("case_001_relationship_supported")

        graph_view = build_graph_view(case)

        self.assertGreater(len(graph_view["nodes"]), 0)
        self.assertGreater(len(graph_view["relationships"]), 0)
        self.assertTrue(
            all(relationship["type"] in DISPLAY_RELATIONSHIP_TYPES for relationship in graph_view["relationships"])
        )

    def test_graph_view_relationships_reference_visible_nodes(self) -> None:
        case = self.repository.get_public_case("case_003_newer_contradiction")

        graph_view = build_graph_view(case)
        node_ids = {node["id"] for node in graph_view["nodes"]}

        for relationship in graph_view["relationships"]:
            self.assertIn(relationship["source"], node_ids)
            self.assertIn(relationship["target"], node_ids)


if __name__ == "__main__":
    unittest.main()
