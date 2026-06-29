from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from backend.app.cases import CaseRepository
from backend.app.graph_retrieval import GraphEvidencePackage, PreparedGraphRetriever
from backend.app.model_explanations import CachedExplanationAdapter
from backend.app.review_engine import DeterministicReviewEngine


class ReviewWorkflowState(TypedDict, total=False):
    case_id: str
    case: Dict[str, Any]
    graph_evidence: GraphEvidencePackage
    review_result: Dict[str, Any]
    citation_retry_count: int
    workflow_trace: List[str]


class ClinicalReviewWorkflow:
    def __init__(
        self,
        repository: CaseRepository,
        graph_retriever: PreparedGraphRetriever | None = None,
        review_engine: DeterministicReviewEngine | None = None,
        explanation_adapter: CachedExplanationAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.graph_retriever = graph_retriever or PreparedGraphRetriever()
        self.review_engine = review_engine or DeterministicReviewEngine(repository, self.graph_retriever)
        self.explanation_adapter = explanation_adapter or CachedExplanationAdapter()
        self.graph = self._build_graph()

    def run(self, case_id: str) -> Dict[str, Any]:
        final_state = self.graph.invoke(
            {
                "case_id": case_id,
                "citation_retry_count": 0,
                "workflow_trace": [],
            }
        )
        return final_state["review_result"]

    def _build_graph(self):
        workflow = StateGraph(ReviewWorkflowState)
        workflow.add_node("load_case", self._load_case)
        workflow.add_node("retrieve_graph_evidence", self._retrieve_graph_evidence)
        workflow.add_node("search_again", self._search_again)
        workflow.add_node("apply_deterministic_rules", self._apply_deterministic_rules)
        workflow.add_node("conflict_analysis", self._conflict_analysis)
        workflow.add_node("generate_model_explanation", self._generate_model_explanation)
        workflow.add_node("citation_validation", self._citation_validation)
        workflow.add_node("retry_invalid_citations", self._retry_invalid_citations)
        workflow.add_node("escalate_to_human", self._escalate_to_human)

        workflow.set_entry_point("load_case")
        workflow.add_edge("load_case", "retrieve_graph_evidence")
        workflow.add_conditional_edges(
            "retrieve_graph_evidence",
            self._route_after_retrieval,
            {
                "search_again": "search_again",
                "apply_rules": "apply_deterministic_rules",
            },
        )
        workflow.add_edge("search_again", "apply_deterministic_rules")
        workflow.add_conditional_edges(
            "apply_deterministic_rules",
            self._route_after_rules,
            {
                "conflict_analysis": "conflict_analysis",
                "explain": "generate_model_explanation",
            },
        )
        workflow.add_edge("conflict_analysis", "generate_model_explanation")
        workflow.add_edge("generate_model_explanation", "citation_validation")
        workflow.add_conditional_edges(
            "citation_validation",
            self._route_after_validation,
            {
                "retry": "retry_invalid_citations",
                "escalate": "escalate_to_human",
                "finish": END,
            },
        )
        workflow.add_edge("retry_invalid_citations", "apply_deterministic_rules")
        workflow.add_edge("escalate_to_human", END)
        return workflow.compile()

    def _load_case(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        return {
            **state,
            "case": self.repository.get_public_case(state["case_id"]),
            "workflow_trace": self._append_trace(state, "load_case"),
        }

    def _retrieve_graph_evidence(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        return {
            **state,
            "graph_evidence": self.graph_retriever.retrieve_for_submitted_diagnosis(state["case"]),
            "workflow_trace": self._append_trace(state, "retrieve_graph_evidence"),
        }

    def _search_again(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        return {
            **state,
            "graph_evidence": self.graph_retriever.retrieve_for_submitted_diagnosis(state["case"]),
            "workflow_trace": self._append_trace(state, "search_again"),
        }

    def _apply_deterministic_rules(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        review_result = self.review_engine.review_loaded_case(
            state["case_id"],
            state["case"],
            state["graph_evidence"],
        )
        review_result["workflow_trace"] = self._append_trace(state, "apply_deterministic_rules")
        review_result["workflow_engine"] = "langgraph"
        return {
            **state,
            "review_result": review_result,
            "workflow_trace": review_result["workflow_trace"],
        }

    def _conflict_analysis(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        review_result = {
            **state["review_result"],
            "conflict_analysis": {
                "has_conflict": True,
                "contradictory_evidence_ids": state["review_result"]["contradictory_evidence_ids"],
            },
        }
        review_result["workflow_trace"] = self._append_trace(state, "conflict_analysis")
        return {
            **state,
            "review_result": review_result,
            "workflow_trace": review_result["workflow_trace"],
        }

    def _generate_model_explanation(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        model_explanation = self.explanation_adapter.explain(state["review_result"])
        review_result = {
            **state["review_result"],
            "explanation": model_explanation.explanation,
            "model": model_explanation.to_dict(),
        }
        review_result["workflow_trace"] = self._append_trace(state, "generate_model_explanation")
        return {
            **state,
            "review_result": review_result,
            "workflow_trace": review_result["workflow_trace"],
        }

    def _citation_validation(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        review_result = {**state["review_result"]}
        review_result["workflow_trace"] = self._append_trace(state, "citation_validation")
        return {
            **state,
            "review_result": review_result,
            "workflow_trace": review_result["workflow_trace"],
        }

    def _retry_invalid_citations(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        return {
            **state,
            "citation_retry_count": state.get("citation_retry_count", 0) + 1,
            "graph_evidence": self.graph_retriever.retrieve_for_submitted_diagnosis(state["case"]),
            "workflow_trace": self._append_trace(state, "retry_invalid_citations"),
        }

    def _escalate_to_human(self, state: ReviewWorkflowState) -> ReviewWorkflowState:
        model_explanation = self.explanation_adapter.explain(
            {
                **state["review_result"],
                "status": "requires_expert_review",
                "missing_requirements": state["review_result"].get("missing_requirements", []),
                "contradictory_evidence_ids": state["review_result"].get("contradictory_evidence_ids", []),
            }
        )
        review_result = {
            **state["review_result"],
            "status": "requires_expert_review",
            "rule_result": "requires_expert_review",
            "explanation": model_explanation.explanation,
            "model": model_explanation.to_dict(),
        }
        review_result["workflow_trace"] = self._append_trace(state, "escalate_to_human")
        return {
            **state,
            "review_result": review_result,
            "workflow_trace": review_result["workflow_trace"],
        }

    @staticmethod
    def _route_after_retrieval(state: ReviewWorkflowState) -> str:
        if not state["graph_evidence"].supporting_evidence_ids and "search_again" not in state.get("workflow_trace", []):
            return "search_again"
        return "apply_rules"

    @staticmethod
    def _route_after_rules(state: ReviewWorkflowState) -> str:
        if state["review_result"]["contradictory_evidence_ids"]:
            return "conflict_analysis"
        return "explain"

    @staticmethod
    def _route_after_validation(state: ReviewWorkflowState) -> str:
        if state["review_result"]["validation"]["valid"]:
            return "finish"
        if state.get("citation_retry_count", 0) < 1:
            return "retry"
        return "escalate"

    @staticmethod
    def _append_trace(state: ReviewWorkflowState, step: str) -> List[str]:
        return [*state.get("workflow_trace", []), step]
