from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


CACHED_EXPLANATIONS = {
    "supported": (
        "The submitted diagnosis is supported by current synthetic chart evidence. "
        "The retrieved notes document Type 2 diabetes, CKD stage 3, their relationship, "
        "and current assessment or management, with no newer contradiction found."
    ),
    "unsupported": (
        "The submitted diagnosis is not supported because the graph did not retrieve "
        "policy-relevant evidence for the submitted condition."
    ),
    "insufficient_evidence": (
        "The retrieved chart evidence supports part of the submitted diagnosis, but the "
        "configured policy requirements are not fully satisfied. A reviewer should request "
        "additional documentation or review the missing requirements."
    ),
    "contradicted": (
        "The submitted diagnosis has older supporting evidence, but newer synthetic chart "
        "evidence conflicts with the CKD stage 3 documentation or the required diabetes-CKD "
        "relationship. Human review is needed before approval."
    ),
    "requires_expert_review": (
        "The workflow could not safely finalize the result after validation, so the case "
        "should be escalated to a human expert."
    ),
}


@dataclass(frozen=True)
class ModelExplanation:
    explanation: str
    model_name: str
    mode: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "model_name": self.model_name,
            "mode": self.mode,
        }


class CachedExplanationAdapter:
    """Produces deterministic reviewer text until MedGemma inference is available."""

    model_name = "cached-medgemma-placeholder"
    mode = "cached_fallback"

    def explain(self, review_result: Dict[str, Any]) -> ModelExplanation:
        status = review_result["status"]
        explanation = CACHED_EXPLANATIONS.get(status, review_result["explanation"])

        missing_labels = [requirement["label"] for requirement in review_result["missing_requirements"]]
        if missing_labels:
            explanation = f"{explanation} Missing requirements: {', '.join(missing_labels)}."

        contradictory_ids = review_result["contradictory_evidence_ids"]
        if contradictory_ids:
            explanation = f"{explanation} Contradictory evidence IDs: {', '.join(contradictory_ids)}."

        return ModelExplanation(
            explanation=explanation,
            model_name=self.model_name,
            mode=self.mode,
        )
