import unittest
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.entity_relation_extraction import RuntimeGraphExtractor
from backend.app.graph_retrieval import PreparedGraphRetriever


class PreparedGraphRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")
        self.retriever = PreparedGraphRetriever()

    def test_retrieves_relationship_evidence_for_supported_case(self) -> None:
        case = self.repository.get_public_case("case_001_relationship_supported")

        evidence_package = self.retriever.retrieve_for_submitted_diagnosis(case)

        self.assertEqual(case["graph"]["relationship_source"], "deterministic_extraction")
        self.assertIn("NOTE-001", evidence_package.supporting_evidence_ids)
        self.assertIn("REQ-003", evidence_package.satisfied_requirement_ids)
        self.assertIn(
            {
                "source": "NOTE-001",
                "relationship": "SUPPORTS_RELATIONSHIP",
                "target": "REL-DM2-CKD3",
            },
            evidence_package.graph_paths,
        )

    def test_separate_condition_case_has_no_relationship_satisfaction(self) -> None:
        case = self.repository.get_public_case("case_002_insufficient_evidence")

        evidence_package = self.retriever.retrieve_for_submitted_diagnosis(case)

        self.assertIn("NOTE-002", evidence_package.supporting_evidence_ids)
        self.assertIn("NOTE-003", evidence_package.supporting_evidence_ids)
        self.assertNotIn("REQ-003", evidence_package.satisfied_requirement_ids)
        self.assertNotIn("REQ-005", evidence_package.satisfied_requirement_ids)

    def test_retrieves_newer_contradiction_evidence(self) -> None:
        case = self.repository.get_public_case("case_003_newer_contradiction")

        evidence_package = self.retriever.retrieve_for_submitted_diagnosis(case)

        self.assertEqual(
            evidence_package.contradictory_evidence_ids,
            ["LAB-011", "LAB-012", "NOTE-005", "NOTE-023"],
        )
        self.assertIn("REQ-006", evidence_package.failed_requirement_ids)
        self.assertIn(
            {
                "source": "NOTE-005",
                "relationship": "SUPERSEDES",
                "target": "NOTE-004",
            },
            evidence_package.graph_paths,
        )

    def test_medgemma_extractor_uses_model_relationships_and_validates_ids(self) -> None:
        case = self.repository.get_public_case("case_001_relationship_supported")
        extractor = RuntimeGraphExtractor(extractor_provider="medgemma_local_http")
        extractor._chat_completion = lambda prompt, max_tokens: """
        {
          "relationships": [
            {"source": "NOTE-001", "type": "DOCUMENTS", "target": "COND-DM2", "rationale": "documents diabetes"},
            {"source": "NOTE-001", "type": "SUPPORTS_RELATIONSHIP", "target": "REL-DM2-CKD3", "rationale": "explicitly links diabetes and CKD"},
            {"source": "NOTE-001", "type": "SATISFIES", "target": "REQ-003", "rationale": "relationship requirement satisfied"},
            {"source": "FAKE-NOTE", "type": "DOCUMENTS", "target": "COND-DM2", "rationale": "invalid source should be dropped"},
            {"source": "NOTE-001", "type": "UNSAFE_TYPE", "target": "COND-DM2", "rationale": "invalid type should be dropped"}
          ]
        }
        """

        graph = extractor.build_graph(case)

        self.assertEqual(graph["relationship_source"], "medgemma_semantic_extraction")
        self.assertIn(
            {"source": "NOTE-001", "type": "SUPPORTS_RELATIONSHIP", "target": "REL-DM2-CKD3"},
            graph["relationships"],
        )
        self.assertNotIn(
            {"source": "FAKE-NOTE", "type": "DOCUMENTS", "target": "COND-DM2"},
            graph["relationships"],
        )


if __name__ == "__main__":
    unittest.main()
