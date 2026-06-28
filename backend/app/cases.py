from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_PUBLIC_FILES = (
    "patient.json",
    "claim.json",
    "conditions.json",
    "encounters.json",
    "notes.json",
    "labs.json",
    "policy.json",
    "graph.json",
)

EXPECTED_RESULT_FILE = "expected_result.json"


class CaseNotFoundError(Exception):
    """Raised when a requested synthetic case does not exist."""


class CaseDataError(Exception):
    """Raised when a synthetic case is missing required data."""


@dataclass(frozen=True)
class CaseSummary:
    id: str
    patient_id: str
    patient_name: str
    review_year: int
    submitted_diagnosis: str
    title: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "review_year": self.review_year,
            "submitted_diagnosis": self.submitted_diagnosis,
            "title": self.title,
        }


class CaseRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def list_cases(self) -> List[Dict[str, Any]]:
        return [self._build_summary(case_dir).to_dict() for case_dir in self._case_dirs()]

    def get_public_case(self, case_id: str) -> Dict[str, Any]:
        case_dir = self.data_dir / case_id
        if not case_dir.is_dir():
            raise CaseNotFoundError(f"Case not found: {case_id}")

        self._validate_required_files(case_dir)
        payload = {"id": case_id}
        for file_name in REQUIRED_PUBLIC_FILES:
            payload[file_name.removesuffix(".json")] = self._read_json(case_dir / file_name)
        return payload

    def get_expected_result(self, case_id: str) -> Dict[str, Any]:
        case_dir = self.data_dir / case_id
        if not case_dir.is_dir():
            raise CaseNotFoundError(f"Case not found: {case_id}")
        expected_path = case_dir / EXPECTED_RESULT_FILE
        if not expected_path.is_file():
            raise CaseDataError(f"Missing expected result file: {expected_path}")
        return self._read_json(expected_path)

    def _case_dirs(self) -> List[Path]:
        if not self.data_dir.is_dir():
            raise CaseDataError(f"Data directory does not exist: {self.data_dir}")
        return sorted(path for path in self.data_dir.iterdir() if path.is_dir())

    def _build_summary(self, case_dir: Path) -> CaseSummary:
        self._validate_required_files(case_dir)
        patient = self._read_json(case_dir / "patient.json")
        claim = self._read_json(case_dir / "claim.json")
        diagnosis = claim["submitted_diagnoses"][0]["label"]

        return CaseSummary(
            id=case_dir.name,
            patient_id=patient["id"],
            patient_name=patient["name"],
            review_year=patient["review_year"],
            submitted_diagnosis=diagnosis,
            title=self._title_from_case_id(case_dir.name),
        )

    def _validate_required_files(self, case_dir: Path) -> None:
        missing = [file_name for file_name in REQUIRED_PUBLIC_FILES if not (case_dir / file_name).is_file()]
        if missing:
            raise CaseDataError(f"Case {case_dir.name} is missing required files: {', '.join(missing)}")

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _title_from_case_id(case_id: str) -> str:
        title = case_id.removeprefix("case_")
        title = title.replace("_", " ")
        return title.title()


def default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


case_repository = CaseRepository(default_data_dir())

