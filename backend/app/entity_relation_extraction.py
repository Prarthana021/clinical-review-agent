from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Set, Tuple


Relationship = Dict[str, str]


class RuntimeGraphExtractor:
    """Builds review graph relationships from case text at runtime.

    The MVP case files still provide the entities and source documents. This
    extractor derives the edges from claim, note, lab, and policy content so the
    running review is not dependent on pre-authored evidence relationships.
    """

    def build_graph(self, case: Dict[str, Any]) -> Dict[str, Any]:
        relationships: List[Relationship] = []
        relationships.extend(self._structural_relationships(case))
        relationships.extend(self._note_relationships(case))
        relationships.extend(self._lab_relationships(case))
        relationships.extend(self._policy_satisfaction_relationships(case, relationships))
        relationships.extend(self._temporal_conflict_relationships(case, relationships))

        return {
            **case["graph"],
            "relationships": self._dedupe_relationships(relationships),
            "relationship_source": "runtime_text_extraction",
        }

    def _structural_relationships(self, case: Dict[str, Any]) -> List[Relationship]:
        patient_id = case["patient"]["id"]
        claim = case["claim"]
        policy = case["policy"]
        submitted_diagnosis = claim["submitted_diagnoses"][0]
        relationships: List[Relationship] = [
            self._rel(patient_id, "HAS_CLAIM", claim["id"]),
            self._rel(claim["id"], "SUBMITS", submitted_diagnosis["id"]),
            self._rel(submitted_diagnosis["id"], "GOVERNED_BY", policy["id"]),
        ]

        condition_ids = {condition["id"] for condition in case["conditions"]["conditions"]}
        for condition_id in condition_ids:
            if self._submitted_diagnosis_mentions_condition(submitted_diagnosis["label"], condition_id):
                relationships.append(self._rel(submitted_diagnosis["id"], "INCLUDES_CONDITION", condition_id))

        required_relationship_id = submitted_diagnosis.get("requires_relationship_id")
        if required_relationship_id:
            relationships.append(self._rel(submitted_diagnosis["id"], "REQUIRES_RELATIONSHIP", required_relationship_id))

        for encounter in case["encounters"]["encounters"]:
            relationships.append(self._rel(patient_id, "HAS_ENCOUNTER", encounter["id"]))

        for note in case["notes"]["notes"]:
            relationships.append(self._rel(note["encounter_id"], "HAS_NOTE", note["id"]))

        for lab in case["labs"]["labs"]:
            relationships.append(self._rel(lab["id"], "RECORDED_DURING", lab["encounter_id"]))

        for requirement in policy["requirements"]:
            relationships.append(self._rel(policy["id"], "HAS_REQUIREMENT", requirement["id"]))

        return relationships

    def _note_relationships(self, case: Dict[str, Any]) -> List[Relationship]:
        relationships: List[Relationship] = []
        relationship_id = self._required_relationship_id(case)

        for note in case["notes"]["notes"]:
            text = self._normalise(note["text"])
            condition_ids = self._conditions_in_text(text)
            for condition_id in condition_ids:
                if self._contradicts_condition(text, condition_id):
                    relationships.append(self._rel(note["id"], "CONTRADICTS", condition_id))
                elif not self._negates_condition_documentation(text, condition_id):
                    relationships.append(self._rel(note["id"], "DOCUMENTS", condition_id))

                if self._actively_assesses(text, condition_id):
                    relationships.append(self._rel(note["id"], "ACTIVELY_ASSESSES", condition_id))

            if relationship_id and self._supports_required_relationship(text):
                relationships.append(self._rel(note["id"], "SUPPORTS_RELATIONSHIP", relationship_id))

            if relationship_id and self._contradicts_required_relationship(text):
                relationships.append(self._rel(note["id"], "CONTRADICTS_RELATIONSHIP", relationship_id))

        return relationships

    def _lab_relationships(self, case: Dict[str, Any]) -> List[Relationship]:
        relationships: List[Relationship] = []
        for lab in case["labs"]["labs"]:
            test = self._normalise(lab["test"])
            interpretation = self._normalise(lab.get("interpretation", ""))
            value = lab.get("value")

            if "egfr" in test and isinstance(value, (int, float)):
                if 30 <= value < 60:
                    relationships.append(self._rel(lab["id"], "SUPPORTS", "COND-CKD3"))
                elif value >= 60:
                    relationships.append(self._rel(lab["id"], "WEAKENS", "COND-CKD3"))

            if "creatinine" in test and isinstance(value, (int, float)):
                if value >= 1.3 or "elevated" in interpretation or "reduced kidney" in interpretation:
                    relationships.append(self._rel(lab["id"], "SUPPORTS", "COND-CKD3"))
                elif value <= 1.1:
                    relationships.append(self._rel(lab["id"], "WEAKENS", "COND-CKD3"))

            if ("a1c" in test or "hemoglobin a1c" in test) and isinstance(value, (int, float)):
                relationships.append(self._rel(lab["id"], "SUPPORTS", "COND-DM2"))

            if "albumin" in test or "acr" in test:
                relationships.append(self._rel(lab["id"], "SUPPORTS", "COND-CKD3"))

        return relationships

    def _policy_satisfaction_relationships(
        self,
        case: Dict[str, Any],
        relationships: List[Relationship],
    ) -> List[Relationship]:
        review_year = case["patient"]["review_year"]
        additions: List[Relationship] = []

        relationship_types_by_source = self._relationship_types_by_source(relationships)
        dated_sources = self._source_dates(case)

        for source_id, relationship_types in relationship_types_by_source.items():
            if "DOCUMENTS:COND-DM2" in relationship_types or "SUPPORTS:COND-DM2" in relationship_types:
                additions.append(self._rel(source_id, "SATISFIES", "REQ-001"))
            if "DOCUMENTS:COND-CKD3" in relationship_types or "SUPPORTS:COND-CKD3" in relationship_types:
                additions.append(self._rel(source_id, "SATISFIES", "REQ-002"))
            if "SUPPORTS_RELATIONSHIP:REL-DM2-CKD3" in relationship_types:
                additions.append(self._rel(source_id, "SATISFIES", "REQ-003"))
            if self._is_current_year(dated_sources.get(source_id), review_year) and any(
                relationship_type.startswith(("DOCUMENTS:", "SUPPORTS:", "SUPPORTS_RELATIONSHIP:"))
                for relationship_type in relationship_types
            ):
                additions.append(self._rel(source_id, "SATISFIES", "REQ-004"))
            if (
                "SUPPORTS_RELATIONSHIP:REL-DM2-CKD3" in relationship_types
                or "ACTIVELY_ASSESSES:COND-CKD3" in relationship_types
            ):
                additions.append(self._rel(source_id, "SATISFIES", "REQ-005"))
            if any(
                relationship_type.startswith(("CONTRADICTS:", "CONTRADICTS_RELATIONSHIP:", "WEAKENS:"))
                for relationship_type in relationship_types
            ):
                additions.append(self._rel(source_id, "FAILS_TO_SATISFY", "REQ-006"))

        return additions

    def _temporal_conflict_relationships(
        self,
        case: Dict[str, Any],
        relationships: List[Relationship],
    ) -> List[Relationship]:
        additions: List[Relationship] = []
        source_dates = self._source_dates(case)
        support_sources = {
            rel["source"]
            for rel in relationships
            if rel["type"] in {"SUPPORTS_RELATIONSHIP", "DOCUMENTS", "SUPPORTS"}
        }
        contradiction_sources = {
            rel["source"]
            for rel in relationships
            if rel["type"] in {"CONTRADICTS", "CONTRADICTS_RELATIONSHIP", "WEAKENS"}
        }

        for contradiction_source in contradiction_sources:
            contradiction_date = source_dates.get(contradiction_source)
            if not contradiction_date:
                continue
            for support_source in support_sources:
                support_date = source_dates.get(support_source)
                if support_date and support_date < contradiction_date:
                    additions.append(self._rel(contradiction_source, "SUPERSEDES", support_source))

        for note in case["notes"]["notes"]:
            text = self._normalise(note["text"])
            if "copied from prior" not in text and "imported chart history" not in text:
                continue
            copied_date = self._parse_date(note["date"])
            earlier_supports = [
                source_id
                for source_id in support_sources
                if source_id.startswith("NOTE-")
                and source_dates.get(source_id)
                and copied_date
                and source_dates[source_id] < copied_date
            ]
            if earlier_supports:
                latest_source = max(earlier_supports, key=lambda source_id: source_dates[source_id])
                additions.append(self._rel(note["id"], "COPIED_FROM", latest_source))

        return additions

    @staticmethod
    def _rel(source: str, relationship_type: str, target: str) -> Relationship:
        return {"source": source, "type": relationship_type, "target": target}

    @staticmethod
    def _dedupe_relationships(relationships: List[Relationship]) -> List[Relationship]:
        seen: Set[Tuple[str, str, str]] = set()
        deduped: List[Relationship] = []
        for relationship in relationships:
            key = (relationship["source"], relationship["type"], relationship["target"])
            if key not in seen:
                seen.add(key)
                deduped.append(relationship)
        return deduped

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(text.lower().replace("-", " ").split())

    @staticmethod
    def _required_relationship_id(case: Dict[str, Any]) -> str | None:
        return case["claim"]["submitted_diagnoses"][0].get("requires_relationship_id")

    def _conditions_in_text(self, text: str) -> Set[str]:
        conditions: Set[str] = set()
        if any(term in text for term in ("type 2 diabetes", "diabetes mellitus", "diabetes")):
            conditions.add("COND-DM2")
        if any(term in text for term in ("chronic kidney disease stage 3", "ckd stage 3", "kidney disease stage 3")):
            conditions.add("COND-CKD3")
        return conditions

    def _submitted_diagnosis_mentions_condition(self, diagnosis_label: str, condition_id: str) -> bool:
        return condition_id in self._conditions_in_text(self._normalise(diagnosis_label))

    @staticmethod
    def _supports_required_relationship(text: str) -> bool:
        relationship_phrases = (
            "diabetes mellitus with chronic kidney disease",
            "diabetes with chronic kidney disease",
            "type 2 diabetes with chronic kidney disease",
            "diabetes related kidney disease",
            "diabetes-associated kidney disease",
            "diabetes associated kidney disease",
        )
        if not any(phrase in text for phrase in relationship_phrases):
            return False
        return not RuntimeGraphExtractor._contradicts_required_relationship(text)

    @staticmethod
    def _contradicts_required_relationship(text: str) -> bool:
        contradiction_phrases = (
            "not currently supported",
            "do not support active chronic kidney disease stage 3",
            "prior ckd stage 3 entry appears outdated",
        )
        return any(phrase in text for phrase in contradiction_phrases)

    @staticmethod
    def _contradicts_condition(text: str, condition_id: str) -> bool:
        if condition_id != "COND-CKD3":
            return False
        contradiction_phrases = (
            "do not support active chronic kidney disease stage 3",
            "ckd stage 3 is not currently supported",
            "prior ckd stage 3 entry appears outdated",
            "remove active ckd stage 3",
        )
        return any(phrase in text for phrase in contradiction_phrases)

    @staticmethod
    def _negates_condition_documentation(text: str, condition_id: str) -> bool:
        if condition_id == "COND-CKD3":
            negation_phrases = (
                "no kidney assessment",
                "no renal assessment",
                "without current assessment",
                "no independent assessment",
                "not currently supported",
            )
            return any(phrase in text for phrase in negation_phrases)
        return False

    @staticmethod
    def _actively_assesses(text: str, condition_id: str) -> bool:
        if RuntimeGraphExtractor._negates_condition_documentation(text, condition_id):
            return False
        if RuntimeGraphExtractor._contradicts_condition(text, condition_id):
            return False
        action_terms = (
            "continue",
            "monitoring",
            "management",
            "regimen",
            "repeat",
            "follow up",
            "follow-up",
            "therapy",
            "treatment",
            "assessment and plan",
        )
        return any(term in text for term in action_terms)

    @staticmethod
    def _relationship_types_by_source(relationships: List[Relationship]) -> Dict[str, Set[str]]:
        grouped: Dict[str, Set[str]] = {}
        for relationship in relationships:
            grouped.setdefault(relationship["source"], set()).add(
                f"{relationship['type']}:{relationship['target']}"
            )
        return grouped

    @staticmethod
    def _source_dates(case: Dict[str, Any]) -> Dict[str, date]:
        dates: Dict[str, date] = {}
        for note in case["notes"]["notes"]:
            parsed_date = RuntimeGraphExtractor._parse_date(note["date"])
            if parsed_date:
                dates[note["id"]] = parsed_date
        for lab in case["labs"]["labs"]:
            parsed_date = RuntimeGraphExtractor._parse_date(lab["date"])
            if parsed_date:
                dates[lab["id"]] = parsed_date
        return dates

    @staticmethod
    def _parse_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _is_current_year(value: date | None, review_year: int) -> bool:
        return value is not None and value.year == review_year


runtime_graph_extractor = RuntimeGraphExtractor()
