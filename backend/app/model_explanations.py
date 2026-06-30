from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Protocol

from backend.app.settings import AppSettings


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
    proposed_status: str | None = None
    raw_response: str | None = None

    def to_dict(self) -> Dict[str, str | None]:
        model_data: Dict[str, str | None] = {
            "model_name": self.model_name,
            "mode": self.mode,
            "proposed_status": self.proposed_status,
        }
        if self.raw_response:
            model_data["raw_response"] = self.raw_response
        return model_data


class ExplanationAdapter(Protocol):
    def explain(self, review_result: Dict[str, Any]) -> ModelExplanation:
        ...


class ModelConfigurationError(Exception):
    """Raised when a model provider cannot be configured."""


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
            proposed_status=status,
        )


class MedGemmaExplanationAdapter:
    """Live MedGemma explanation adapter using Hugging Face Transformers.

    The deterministic rule result remains authoritative. This adapter receives
    the rule result and evidence IDs, then generates reviewer-friendly wording.
    """

    mode = "live_medgemma"

    def __init__(self, model_id: str, huggingface_token: str | None = None) -> None:
        self.model_id = model_id
        self.huggingface_token = huggingface_token
        self._pipeline = None

    def explain(self, review_result: Dict[str, Any]) -> ModelExplanation:
        try:
            text_generator = self._load_pipeline()
            prompt = self._build_prompt(review_result)
            output = text_generator(prompt, max_new_tokens=180, do_sample=False)
            generated_text = output[0]["generated_text"]
            explanation = generated_text.removeprefix(prompt).strip() or review_result["explanation"]
        except Exception as exc:
            fallback = CachedExplanationAdapter().explain(review_result)
            return ModelExplanation(
                explanation=(
                    f"{fallback.explanation} Live MedGemma was requested but unavailable: "
                    f"{type(exc).__name__}."
                ),
                model_name=self.model_id,
                mode="cached_fallback_after_medgemma_error",
                proposed_status=review_result["status"],
            )

        parsed = self._parse_model_response(explanation)
        if parsed:
            explanation = parsed.get("explanation") or review_result["explanation"]
            proposed_status = parsed.get("status") or review_result["status"]
        else:
            proposed_status = review_result["status"]

        return ModelExplanation(
            explanation=explanation,
            model_name=self.model_id,
            mode=self.mode,
            proposed_status=proposed_status,
            raw_response=generated_text,
        )

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ModelConfigurationError(
                "MODEL_PROVIDER=medgemma requires optional dependencies from backend/requirements-medgemma.txt."
            ) from exc

        pipeline_kwargs: Dict[str, Any] = {
            "task": "text-generation",
            "model": self.model_id,
            "device_map": "auto",
        }
        if self.huggingface_token:
            pipeline_kwargs["token"] = self.huggingface_token

        self._pipeline = pipeline(**pipeline_kwargs)
        return self._pipeline

    @staticmethod
    def _build_prompt(review_result: Dict[str, Any]) -> str:
        return (
            "You are assisting a clinical documentation reviewer. "
            "Return JSON only. Explain the deterministic review result in concise, evidence-grounded language. "
            "Do not change the status. Do not invent evidence.\n\n"
            f"Submitted diagnosis: {review_result['submitted_diagnosis']}\n"
            f"Rule status: {review_result['status']}\n"
            f"Supporting evidence IDs: {', '.join(review_result['supporting_evidence_ids']) or 'none'}\n"
            f"Contradictory evidence IDs: {', '.join(review_result['contradictory_evidence_ids']) or 'none'}\n"
            f"Missing requirement IDs: {', '.join(review_result['missing_requirement_ids']) or 'none'}\n\n"
            'JSON schema: {"status": "<same as Rule status>", "explanation": "<reviewer-facing explanation>"}\n'
            "JSON:"
        )

    @staticmethod
    def _parse_model_response(text: str) -> Dict[str, str] | None:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return {
            key: value
            for key, value in parsed.items()
            if key in {"status", "explanation"} and isinstance(value, str)
        }


def build_explanation_adapter(settings: AppSettings) -> ExplanationAdapter:
    if settings.model_provider == "cached":
        return CachedExplanationAdapter()
    if settings.model_provider == "medgemma":
        return MedGemmaExplanationAdapter(
            model_id=settings.medgemma_model_id,
            huggingface_token=settings.huggingface_token,
        )
    raise ModelConfigurationError(f"Unsupported model provider: {settings.model_provider}")
