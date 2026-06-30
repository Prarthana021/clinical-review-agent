import tempfile
import unittest
from pathlib import Path

from backend.app.cases import CaseRepository
from backend.app.vector_retrieval import ChromaVectorRetriever


class ChromaVectorRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.repository = CaseRepository(repo_root / "data")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.retriever = ChromaVectorRetriever(Path(self.temp_dir.name) / "chroma")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_retrieves_semantic_evidence_from_notes_and_labs(self) -> None:
        case = self.repository.get_public_case("case_001_relationship_supported")

        results = self.retriever.retrieve_for_case(case, limit=4)

        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(all(result.evidence_id.startswith(("NOTE-", "LAB-")) for result in results))
        self.assertTrue(all(result.score > 0 for result in results))


if __name__ == "__main__":
    unittest.main()
