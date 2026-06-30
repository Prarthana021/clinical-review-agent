export type CaseSummary = {
  id: string;
  patient_id: string;
  patient_name: string;
  review_year: number;
  submitted_diagnosis: string;
  title: string;
};

export type GraphPath = {
  source: string;
  relationship: string;
  target: string;
};

export type GraphNode = {
  id: string;
  type: string;
  label: string;
};

export type GraphRelationship = {
  source: string;
  type: string;
  target: string;
};

export type CaseGraph = {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
};

export type EvidenceItem =
  | {
      id: string;
      kind: "note";
      title: string;
      date: string;
      page: number;
      section: string;
      text: string;
      encounter_id: string;
    }
  | {
      id: string;
      kind: "lab";
      title: string;
      date: string;
      value: number;
      unit: string;
      interpretation: string;
      encounter_id: string;
    };

export type PolicyRequirement = {
  id: string;
  label: string;
  description: string;
};

export type ReviewResult = {
  review_id: string;
  case_id: string;
  status: "supported" | "unsupported" | "contradicted" | "insufficient_evidence" | "requires_expert_review";
  rule_result: string;
  policy_id: string;
  policy_version: string;
  submitted_diagnosis: string;
  supporting_evidence_ids: string[];
  contradictory_evidence_ids: string[];
  satisfied_requirement_ids: string[];
  missing_requirement_ids: string[];
  supporting_evidence: EvidenceItem[];
  contradictory_evidence: EvidenceItem[];
  satisfied_requirements: PolicyRequirement[];
  missing_requirements: PolicyRequirement[];
  graph_paths: GraphPath[];
  explanation: string;
  workflow_engine?: string;
  workflow_trace?: string[];
  model?: {
    model_name: string;
    mode: string;
    proposed_status?: string | null;
    raw_response?: string | null;
  };
  conflict_analysis?: {
    has_conflict: boolean;
    contradictory_evidence_ids: string[];
  };
  validation: {
    valid: boolean;
    missing_evidence_ids: string[];
    missing_requirement_ids: string[];
    model_status_matches_rule?: boolean;
    model_proposed_status?: string | null;
  };
};

export type ReviewerAction = "approve" | "reject" | "request_documentation" | "escalate";

export type AuditRecord = {
  audit_id: string;
  review_id: string;
  case_id: string;
  submitted_diagnosis: string;
  policy_id: string;
  policy_version: string;
  ai_status: ReviewResult["status"];
  rule_result: string;
  supporting_evidence_ids: string[];
  contradictory_evidence_ids: string[];
  graph_paths: GraphPath[];
  llm_explanation: string;
  model?: {
    model_name: string;
    mode: string;
    proposed_status?: string | null;
    raw_response?: string | null;
  };
  validation: ReviewResult["validation"];
  reviewer_action: ReviewerAction;
  reviewer_comment: string;
  reviewer_id: string;
  decided_at: string;
};

export type EvaluationCaseResult = {
  case_id: string;
  expected_status: ReviewResult["status"];
  actual_status: ReviewResult["status"];
  passed: boolean;
  status_matches: boolean;
  citations_valid: boolean;
  supporting_evidence_recall: boolean;
  contradictory_evidence_recall: boolean;
  graph_paths_present: boolean;
  expected_supporting_evidence_ids: string[];
  actual_supporting_evidence_ids: string[];
  expected_contradictory_evidence_ids: string[];
  actual_contradictory_evidence_ids: string[];
  workflow_trace: string[];
};

export type EvaluationSummary = {
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  cases: EvaluationCaseResult[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchCases(): Promise<CaseSummary[]> {
  const response = await fetch(`${API_BASE_URL}/cases`);
  if (!response.ok) {
    throw new Error(`Failed to load cases: ${response.status}`);
  }
  return response.json();
}

export async function fetchCaseGraph(caseId: string): Promise<CaseGraph> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/graph`);
  if (!response.ok) {
    throw new Error(`Failed to load case graph: ${response.status}`);
  }
  return response.json();
}

export async function runReview(caseId: string): Promise<ReviewResult> {
  const response = await fetch(`${API_BASE_URL}/reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ case_id: caseId }),
  });
  if (!response.ok) {
    throw new Error(`Failed to run review: ${response.status}`);
  }
  return response.json();
}

export async function saveReviewerDecision(
  reviewId: string,
  action: ReviewerAction,
  comment: string,
): Promise<AuditRecord> {
  const response = await fetch(`${API_BASE_URL}/reviews/${reviewId}/decision`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      action,
      comment,
      reviewer_id: "demo-reviewer",
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to save reviewer decision: ${response.status}`);
  }
  return response.json();
}

export async function fetchAuditRecords(): Promise<AuditRecord[]> {
  const response = await fetch(`${API_BASE_URL}/audit`);
  if (!response.ok) {
    throw new Error(`Failed to load audit history: ${response.status}`);
  }
  return response.json();
}

export async function fetchEvaluation(): Promise<EvaluationSummary> {
  const response = await fetch(`${API_BASE_URL}/evaluation`);
  if (!response.ok) {
    throw new Error(`Failed to load evaluation: ${response.status}`);
  }
  return response.json();
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}
