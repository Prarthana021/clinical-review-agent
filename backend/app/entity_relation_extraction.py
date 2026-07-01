from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any, Dict, List, Set, Tuple


Relationship = Dict[str, str]
MODEL_RELATIONSHIP_TYPES = {
    "DOCUMENTS",
    "SUPPORTS",
    "SUPPORTS_RELATIONSHIP",
    "ACTIVELY_ASSESSES",
    "CONTRADICTS",
    "CONTRADICTS_RELATIONSHIP",
    "WEAKENS",
    "SUPERSEDES",
    "COPIED_FROM",
    "SATISFIES",
    "FAILS_TO_SATISFY",
}


class RuntimeGraphExtractor:
    """Builds review graph relationships from case text at runtime.

    The MVP case files still provide the entities and source documents. This
    extractor derives the edges from claim, note, lab, and policy content so the
    running review is not dependent on pre-authored evidence relationships.
    """

    def __init__(
        self,
        extractor_provider: str | None = None,
        local_llm_base_url: str | None = None,
        local_llm_model: str | None = None,
    ) -> None:
        self.extractor_provider = extractor_provider
        self.local_llm_base_url = local_llm_base_url
        self.local_llm_model = local_llm_model

    def build_graph(self, case: Dict[str, Any]) -> Dict[str, Any]:
        structural_relationships = self._structural_relationships(case)
        if self._uses_medgemma_extraction():
            evidence_relationships = self._medgemma_relationships(case)
            relationship_source = "medgemma_semantic_extraction"
        else:
            evidence_relationships = self._deterministic_relationships(case)
            relationship_source = "deterministic_extraction"

        relationships = [*structural_relationships, *evidence_relationships]

        return {
            **case["graph"],
            "relationships": self._dedupe_relationships(relationships),
            "relationship_source": relationship_source,
        }

    def _uses_medgemma_extraction(self) -> bool:
        provider = self.extractor_provider or os.getenv("RELATION_EXTRACTOR_PROVIDER", "auto")
        if provider == "auto":
            return os.getenv("MODEL_PROVIDER") == "local_http"
        return provider in {"medgemma", "local_http", "medgemma_local_http"}

    def _deterministic_relationships(self, case: Dict[str, Any]) -> List[Relationship]:
        relationships: List[Relationship] = []
        relationships.extend(self._note_relationships(case))
        relationships.extend(self._lab_relationships(case))
        relationships.extend(self._policy_satisfaction_relationships(case, relationships))
        relationships.extend(self._temporal_conflict_relationships(case, relationships))
        return relationships

    def _medgemma_relationships(self, case: Dict[str, Any]) -> List[Relationship]:
        raw_response = self._chat_completion(self._build_extraction_prompt(case), max_tokens=1600)
        parsed_relationships = self._parse_model_relationships(raw_response)
        relationships = self._validated_model_relationships(case, parsed_relationships)
        if not relationships:
            raise RuntimeError("MedGemma did not return any valid graph relationships.")
        return relationships

    def _build_extraction_prompt(self, case: Dict[str, Any]) -> str:
        nodes = [
            {"id": node["id"], "type": node["type"], "label": node["label"]}
            for node in case["graph"]["nodes"]
        ]
        notes = [
            {
                "id": note["id"],
                "date": note["date"],
                "type": note["type"],
                "section": note["section"],
                "text": note["text"],
            }
            for note in case["notes"]["notes"]
        ]
        labs = [
            {
                "id": lab["id"],
                "date": lab["date"],
                "test": lab["test"],
                "value": lab["value"],
                "unit": lab["unit"],
                "interpretation": lab.get("interpretation", ""),
            }
            for lab in case["labs"]["labs"]
        ]
        policy_requirements = [
            {
                "id": requirement["id"],
                "label": requirement["label"],
                "description": requirement["description"],
            }
            for requirement in case["policy"]["requirements"]
        ]
        payload = {
            "submitted_diagnosis": case["claim"]["submitted_diagnoses"][0],
            "review_year": case["patient"]["review_year"],
            "available_nodes": nodes,
            "allowed_relationship_types": sorted(MODEL_RELATIONSHIP_TYPES),
            "notes": notes,
            "labs": labs,
            "policy_requirements": policy_requirements,
            "rules": [
                "Return only relationships supported by the provided notes, labs, claim, or policy.",
                "Use DOCUMENTS when a note documents a condition.",
                "Use SUPPORTS when a lab supports a condition.",
                "Use WEAKENS when a lab weakens a condition.",
                "Use SUPPORTS_RELATIONSHIP only when text explicitly connects the submitted conditions.",
                "Do not create SUPPORTS_RELATIONSHIP when conditions are only documented separately.",
                "Use CONTRADICTS or CONTRADICTS_RELATIONSHIP for text that disputes current support.",
                "Use SUPERSEDES when newer evidence replaces older support.",
                "Use SATISFIES only when evidence satisfies a policy requirement.",
                "Use FAILS_TO_SATISFY for unresolved newer contradictory evidence.",
                "source and target must be exact IDs from available_nodes.",
            ],
        }
        return (
            "You are a clinical graph extraction model. Extract semantic graph relationships from the chart. "
            "Return JSON only with this schema: "
            '{"relationships":[{"source":"<node id>","type":"<allowed type>","target":"<node id>","rationale":"short source-grounded reason"}]}. '
            "Do not invent node IDs, evidence, diagnoses, or policy requirements.\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

    def _chat_completion(self, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.local_llm_model or os.getenv("LOCAL_LLM_MODEL") or os.getenv("LM_STUDIO_MODEL", "medgemma-1.5-4b-it"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract evidence-cited clinical graph relationships. "
                        "Return JSON only. Never invent source IDs or target IDs."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            self._chat_completions_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Local MedGemma extraction server returned {exc.code}: {detail}") from exc
        return data["choices"][0]["message"]["content"]

    def _chat_completions_url(self) -> str:
        base_url = (self.local_llm_base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234")).rstrip("/")
        parsed = urllib.parse.urlparse(base_url)
        if parsed.path in ("", "/"):
            return f"{base_url}/v1/chat/completions"
        return f"{base_url}/chat/completions"

    @staticmethod
    def _parse_model_relationships(raw_response: str) -> List[Dict[str, str]]:
        match = re.search(r"\{.*\}", raw_response, flags=re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        relationships = parsed.get("relationships")
        if not isinstance(relationships, list):
            return []
        return [relationship for relationship in relationships if isinstance(relationship, dict)]

    @staticmethod
    def _validated_model_relationships(case: Dict[str, Any], relationships: List[Dict[str, str]]) -> List[Relationship]:
        node_ids = {node["id"] for node in case["graph"]["nodes"]}
        validated: List[Relationship] = []
        for relationship in relationships:
            source = relationship.get("source")
            relationship_type = relationship.get("type")
            target = relationship.get("target")
            if not isinstance(source, str) or not isinstance(relationship_type, str) or not isinstance(target, str):
                continue
            if source not in node_ids or target not in node_ids:
                continue
            if relationship_type not in MODEL_RELATIONSHIP_TYPES:
                continue
            validated.append({"source": source, "type": relationship_type, "target": target})
        return RuntimeGraphExtractor._dedupe_relationships(validated)

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
