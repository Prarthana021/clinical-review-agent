from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_REVIEWER_ACTIONS = {"approve", "reject", "request_documentation", "escalate"}


class AuditLogError(Exception):
    """Raised when review or audit persistence fails."""


class ReviewNotFoundError(Exception):
    """Raised when a reviewer decision references an unknown review."""


class InvalidReviewerActionError(Exception):
    """Raised when a reviewer action is outside the allowed action set."""


class AuditRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_review_result(self, review_result: Dict[str, Any]) -> Dict[str, Any]:
        review_id = str(uuid.uuid4())
        created_at = self._now()
        persisted = {"review_id": review_id, **review_result}

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reviews (
                    review_id,
                    case_id,
                    status,
                    rule_result,
                    submitted_diagnosis,
                    result_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    review_result["case_id"],
                    review_result["status"],
                    review_result["rule_result"],
                    review_result["submitted_diagnosis"],
                    json.dumps(persisted, sort_keys=True),
                    created_at,
                ),
            )
        return persisted

    def save_reviewer_decision(
        self,
        review_id: str,
        action: str,
        comment: str = "",
        reviewer_id: str = "demo-reviewer",
    ) -> Dict[str, Any]:
        if action not in VALID_REVIEWER_ACTIONS:
            raise InvalidReviewerActionError(f"Invalid reviewer action: {action}")

        review = self.get_review_result(review_id)
        if review is None:
            raise ReviewNotFoundError(f"Review not found: {review_id}")

        audit_id = str(uuid.uuid4())
        decided_at = self._now()
        audit_record = {
            "audit_id": audit_id,
            "review_id": review_id,
            "case_id": review["case_id"],
            "submitted_diagnosis": review["submitted_diagnosis"],
            "ai_status": review["status"],
            "rule_result": review["rule_result"],
            "supporting_evidence_ids": review["supporting_evidence_ids"],
            "contradictory_evidence_ids": review["contradictory_evidence_ids"],
            "graph_paths": review["graph_paths"],
            "llm_explanation": review["explanation"],
            "model": review.get("model", {}),
            "validation": review["validation"],
            "reviewer_action": action,
            "reviewer_comment": comment,
            "reviewer_id": reviewer_id,
            "decided_at": decided_at,
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_decisions (
                    audit_id,
                    review_id,
                    case_id,
                    ai_status,
                    reviewer_action,
                    reviewer_comment,
                    reviewer_id,
                    audit_json,
                    decided_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    review_id,
                    review["case_id"],
                    review["status"],
                    action,
                    comment,
                    reviewer_id,
                    json.dumps(audit_record, sort_keys=True),
                    decided_at,
                ),
            )
        return audit_record

    def get_review_result(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM reviews WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["result_json"])

    def list_audit_records(self) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT audit_json FROM audit_decisions ORDER BY decided_at DESC"
            ).fetchall()
        return [json.loads(row["audit_json"]) for row in rows]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rule_result TEXT NOT NULL,
                    submitted_diagnosis TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_decisions (
                    audit_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    ai_status TEXT NOT NULL,
                    reviewer_action TEXT NOT NULL,
                    reviewer_comment TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    audit_json TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


def default_audit_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "audit.sqlite3"


audit_repository = AuditRepository(default_audit_db_path())
