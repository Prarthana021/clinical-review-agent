from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol


@dataclass(frozen=True)
class VectorSearchResult:
    evidence_id: str
    score: float
    text: str


class VectorRetriever(Protocol):
    def retrieve_for_case(self, case: Dict[str, Any], limit: int = 5) -> List[VectorSearchResult]:
        ...


class VectorConfigurationError(Exception):
    """Raised when the selected vector provider cannot be configured."""


class ChromaVectorRetriever:
    """Local ChromaDB vector retrieval over synthetic notes and labs.

    The embedding function is deterministic and local so the POC does not need
    an external embedding API. ChromaDB still provides the vector database,
    persistence, metadata storage, and nearest-neighbor query layer.
    """

    def __init__(self, persist_dir: Path, dimensions: int = 256) -> None:
        self.persist_dir = persist_dir
        self.dimensions = dimensions
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
        except ImportError as exc:
            raise VectorConfigurationError(
                "VECTOR_PROVIDER=chromadb requires chromadb. Install backend/requirements.txt."
            ) from exc

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(name="clinical_review_evidence")

    def retrieve_for_case(self, case: Dict[str, Any], limit: int = 5) -> List[VectorSearchResult]:
        self.index_case(case)
        query = case["claim"]["submitted_diagnoses"][0]["label"]
        result = self._collection.query(
            query_embeddings=[self._embed(query)],
            n_results=limit,
            where={"case_id": case["id"]},
            include=["documents", "distances", "metadatas"],
        )
        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [
            VectorSearchResult(
                evidence_id=metadata["evidence_id"],
                score=1.0 / (1.0 + distance),
                text=document,
            )
            for metadata, document, distance in zip(metadatas, documents, distances)
        ]

    def index_case(self, case: Dict[str, Any]) -> None:
        documents = self._case_documents(case)
        if not documents:
            return

        evidence_ids = list(documents.keys())
        ids = [f"{case['id']}:{evidence_id}" for evidence_id in evidence_ids]
        texts = list(documents.values())
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=[self._embed(text) for text in texts],
            metadatas=[
                {
                    "case_id": case["id"],
                    "evidence_id": evidence_id,
                }
                for evidence_id in evidence_ids
            ],
        )

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return [
            token.strip(".,;:()[]{}\"'").lower()
            for token in text.split()
            if token.strip(".,;:()[]{}\"'")
        ]

    @staticmethod
    def _case_documents(case: Dict[str, Any]) -> Dict[str, str]:
        documents: Dict[str, str] = {}
        for note in case["notes"]["notes"]:
            documents[note["id"]] = f"{note['type']} {note['section']} {note['text']}"
        for lab in case["labs"]["labs"]:
            documents[lab["id"]] = (
                f"{lab['test']} {lab['value']} {lab['unit']} {lab['interpretation']} "
                f"{lab['date']}"
            )
        return documents


class DisabledVectorRetriever:
    def retrieve_for_case(self, case: Dict[str, Any], limit: int = 5) -> List[VectorSearchResult]:
        return []


def default_chroma_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "chroma"


def build_vector_retriever(provider: str) -> VectorRetriever:
    if provider == "disabled":
        return DisabledVectorRetriever()
    if provider == "chromadb":
        return ChromaVectorRetriever(default_chroma_dir())
    raise VectorConfigurationError(f"Unsupported vector provider: {provider}")
