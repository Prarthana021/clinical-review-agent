import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Activity, ArrowRight, ChevronDown, ClipboardCheck, Database, ShieldCheck } from "lucide-react";

import {
  AuditRecord,
  CaseGraph,
  CaseSummary,
  EvidenceItem,
  EvaluationSummary,
  PolicyRequirement,
  ReviewResult,
  ReviewerAction,
  apiBaseUrl,
  fetchAuditRecords,
  fetchCaseGraph,
  fetchCases,
  fetchEvaluation,
  runReview,
  saveReviewerDecision,
} from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "loaded" | "error";
type ReviewState = "idle" | "running" | "complete" | "error";
type DecisionState = "idle" | "saving" | "saved" | "error";
type AuditState = "idle" | "loading" | "loaded" | "error";
type EvaluationState = "idle" | "loading" | "loaded" | "error";
type GraphState = "idle" | "loading" | "loaded" | "error";

function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [reviewState, setReviewState] = useState<ReviewState>("idle");
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [reviewerComment, setReviewerComment] = useState("");
  const [decisionState, setDecisionState] = useState<DecisionState>("idle");
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [auditRecord, setAuditRecord] = useState<AuditRecord | null>(null);
  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([]);
  const [auditState, setAuditState] = useState<AuditState>("idle");
  const [auditError, setAuditError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationSummary | null>(null);
  const [evaluationState, setEvaluationState] = useState<EvaluationState>("idle");
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [caseGraph, setCaseGraph] = useState<CaseGraph | null>(null);
  const [graphState, setGraphState] = useState<GraphState>("idle");
  const [graphError, setGraphError] = useState<string | null>(null);

  async function loadCases() {
    setLoadState("loading");
    setError(null);
    try {
      const loadedCases = await fetchCases();
      setCases(loadedCases);
      setSelectedCaseId((currentCaseId) => currentCaseId ?? loadedCases[0]?.id ?? null);
      setLoadState("loaded");
    } catch (err) {
      setCases([]);
      setError(err instanceof Error ? err.message : "Unable to load cases.");
      setLoadState("error");
    }
  }

  async function loadAuditRecords() {
    setAuditState("loading");
    setAuditError(null);
    try {
      const loadedAuditRecords = await fetchAuditRecords();
      setAuditRecords(loadedAuditRecords);
      setAuditState("loaded");
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : "Unable to load audit history.");
      setAuditState("error");
    }
  }

  async function loadEvaluation() {
    setEvaluationState("loading");
    setEvaluationError(null);
    try {
      const loadedEvaluation = await fetchEvaluation();
      setEvaluation(loadedEvaluation);
      setEvaluationState("loaded");
    } catch (err) {
      setEvaluation(null);
      setEvaluationError(err instanceof Error ? err.message : "Unable to load evaluation.");
      setEvaluationState("error");
    }
  }

  async function loadCaseGraph(caseId: string) {
    setGraphState("loading");
    setGraphError(null);
    try {
      const loadedGraph = await fetchCaseGraph(caseId);
      setCaseGraph(loadedGraph);
      setGraphState("loaded");
    } catch (err) {
      setCaseGraph(null);
      setGraphError(err instanceof Error ? err.message : "Unable to load graph.");
      setGraphState("error");
    }
  }

  useEffect(() => {
    let ignore = false;

    async function loadInitialCases() {
      setLoadState("loading");
      setError(null);
      try {
        const loadedCases = await fetchCases();
        if (!ignore) {
          setCases(loadedCases);
          setSelectedCaseId(loadedCases[0]?.id ?? null);
          setLoadState("loaded");
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Unable to load cases.");
          setLoadState("error");
        }
      }
    }

    loadInitialCases();
    loadAuditRecords();
    loadEvaluation();
    return () => {
      ignore = true;
    };
  }, []);

  const selectedCase = useMemo(
    () => cases.find((caseSummary) => caseSummary.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );

  useEffect(() => {
    if (selectedCaseId) {
      loadCaseGraph(selectedCaseId);
    }
  }, [selectedCaseId]);

  async function handleRunReview() {
    if (!selectedCaseId) {
      return;
    }

    setReviewState("running");
    setReviewError(null);
    setReviewResult(null);
    setDecisionState("idle");
    setDecisionError(null);
    setAuditRecord(null);
    try {
      const result = await runReview(selectedCaseId);
      setReviewResult(result);
      setReviewState("complete");
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Unable to run review.");
      setReviewState("error");
    }
  }

  function handleSelectCase(caseId: string) {
    setSelectedCaseId(caseId);
    setReviewState("idle");
    setReviewError(null);
    setReviewResult(null);
    setReviewerComment("");
    setDecisionState("idle");
    setDecisionError(null);
    setAuditRecord(null);
  }

  async function handleReviewerDecision(action: ReviewerAction) {
    if (!reviewResult) {
      return;
    }

    setDecisionState("saving");
    setDecisionError(null);
    try {
      const savedAuditRecord = await saveReviewerDecision(
        reviewResult.review_id,
        action,
        reviewerComment.trim(),
      );
      setAuditRecord(savedAuditRecord);
      setDecisionState("saved");
      await loadAuditRecords();
    } catch (err) {
      setDecisionError(err instanceof Error ? err.message : "Unable to save reviewer decision.");
      setDecisionState("error");
    }
  }

  return (
    <main className="app-shell">
      <aside className="side-panel" aria-label="Clinical Review Agent overview">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            CR
          </div>
          <div>
            <p className="eyebrow">Clinical Review Agent</p>
            <h1>Review workspace</h1>
          </div>
        </div>

        <section className="metric-group" aria-label="Review process overview">
          <div className="metric-item">
            <ClipboardCheck size={18} aria-hidden="true" />
            <span>Claim already contains diagnosis</span>
          </div>
          <div className="metric-item">
            <Database size={18} aria-hidden="true" />
            <span>Agent gathers chart evidence</span>
          </div>
          <div className="metric-item">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Reviewer records final action</span>
          </div>
        </section>

        <p className="disclaimer">
          Synthetic demo data only. Not for clinical, coding, payment, or compliance decisions.
        </p>
      </aside>

      <section className="workspace" aria-label="Case selection workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Case selection</p>
            <h2>Review an incoming claim packet</h2>
          </div>
          <div className={`status-pill ${loadState === "error" ? "error" : ""}`}>
            <Activity size={16} aria-hidden="true" />
            {loadState === "loaded" ? "Backend connected" : "Backend unavailable"}
          </div>
        </header>

        {loadState === "loading" && <div className="notice">Loading case queue...</div>}
        {loadState === "error" && (
          <div className="notice error">
            <strong>Could not load cases.</strong>
            <span>{error}</span>
            <span>Start the backend at {apiBaseUrl()} and try again.</span>
            <button className="secondary-action" onClick={loadCases} type="button">
              Retry
            </button>
          </div>
        )}

        {loadState === "loaded" && (
          <div className="case-layout">
            <div className="case-list" aria-label="Incoming claim packets">
              {cases.map((caseSummary) => (
                <button
                  className={`case-row ${caseSummary.id === selectedCaseId ? "selected" : ""}`}
                  key={caseSummary.id}
                  onClick={() => handleSelectCase(caseSummary.id)}
                  type="button"
                >
                  <span className="case-row-title">{formatPacketTitle(caseSummary.id)}</span>
                  <span className="case-row-meta">
                    Claim + chart packet · {caseSummary.patient_id} · {caseSummary.review_year}
                  </span>
                </button>
              ))}
            </div>

            <article className="case-detail" aria-label="Selected case details">
              {selectedCase ? (
                <>
                  <div>
                    <p className="eyebrow">Selected packet</p>
                    <h3>{formatPacketTitle(selectedCase.id)}</h3>
                  </div>

                  <dl className="detail-grid">
                    <div>
                      <dt>Patient</dt>
                      <dd>{selectedCase.patient_name}</dd>
                    </div>
                    <div>
                      <dt>Patient ID</dt>
                      <dd>{selectedCase.patient_id}</dd>
                    </div>
                    <div>
                      <dt>Review year</dt>
                      <dd>{selectedCase.review_year}</dd>
                    </div>
                  </dl>

                  <section className="diagnosis-panel">
                    <span>Submitted diagnosis</span>
                    <strong>{selectedCase.submitted_diagnosis}</strong>
                    <small>This diagnosis comes from the claim file in this review packet.</small>
                  </section>

                  <section className="intake-panel" aria-label="Review packet documents">
                    <div>
                      <p className="eyebrow">Document intake</p>
                      <h5>Claim and chart sources</h5>
                    </div>
                    <div className="intake-grid">
                      <div>
                        <span>Claim file</span>
                        <strong>Submitted diagnosis, member, service year</strong>
                      </div>
                      <div>
                        <span>Medical record</span>
                        <strong>Clinical notes, labs, encounters</strong>
                      </div>
                      <div>
                        <span>Review policy</span>
                        <strong>Synthetic documentation requirements</strong>
                      </div>
                    </div>
                    <small>
                      This MVP uses prepared synthetic packets instead of parsing uploaded records.
                    </small>
                  </section>

                  <button
                    className="primary-action"
                    disabled={reviewState === "running"}
                    onClick={handleRunReview}
                    type="button"
                  >
                    {reviewState === "running" ? "Running review" : "Run packet review"}
                    <ArrowRight size={17} aria-hidden="true" />
                  </button>

                  {reviewState === "error" && (
                    <div className="notice error">
                      <strong>Review failed.</strong>
                      <span>{reviewError}</span>
                    </div>
                  )}

                  {reviewResult && (
                    <section className="review-result" aria-label="Review result">
                      <div className="review-result-header">
                        <div>
                          <p className="eyebrow">Agent review</p>
                          <h4>{formatStatus(reviewResult.status)}</h4>
                        </div>
                        <span className={`result-badge ${reviewResult.status}`}>
                          {reviewResult.validation.valid ? "Citations valid" : "Citation issue"}
                        </span>
                      </div>

                      <p className="result-explanation">{reviewResult.explanation}</p>
                      {reviewResult.model && (
                        <div className="model-pill">
                          <span>Explanation source</span>
                          <strong>{formatModelMode(reviewResult.model.mode)}</strong>
                        </div>
                      )}

                      <section className="reviewer-actions" aria-label="Reviewer action">
                        <div>
                          <p className="eyebrow">Human decision</p>
                          <h5>Record reviewer action</h5>
                        </div>

                        <label className="comment-field">
                          <span>Reviewer comment</span>
                          <textarea
                            onChange={(event) => setReviewerComment(event.target.value)}
                            placeholder="Add a short note for the audit log."
                            rows={3}
                            value={reviewerComment}
                          />
                        </label>

                        <div className="action-row">
                          <DecisionButton
                            action="approve"
                            disabled={decisionState === "saving"}
                            label="Approve"
                            onClick={handleReviewerDecision}
                          />
                          <DecisionButton
                            action="reject"
                            disabled={decisionState === "saving"}
                            label="Reject"
                            onClick={handleReviewerDecision}
                          />
                          <DecisionButton
                            action="request_documentation"
                            disabled={decisionState === "saving"}
                            label="Request Documentation"
                            onClick={handleReviewerDecision}
                          />
                          <DecisionButton
                            action="escalate"
                            disabled={decisionState === "saving"}
                            label="Escalate"
                            onClick={handleReviewerDecision}
                          />
                        </div>

                        {decisionState === "saving" && <p className="helper-text">Saving reviewer decision...</p>}
                        {decisionState === "error" && (
                          <div className="notice error">
                            <strong>Could not save decision.</strong>
                            <span>{decisionError}</span>
                          </div>
                        )}
                        {auditRecord && (
                          <div className={`audit-confirmation ${auditRecord.reviewer_action}`}>
                            <span>Audit saved</span>
                            <strong>{formatAction(auditRecord.reviewer_action)}</strong>
                            <small>Audit ID: {auditRecord.audit_id}</small>
                          </div>
                        )}
                      </section>

                      <div className="review-details">
                        <CollapsibleSection
                          count={reviewResult.supporting_evidence.length}
                          defaultOpen
                          title="Supporting evidence"
                        >
                          <EvidenceCards items={reviewResult.supporting_evidence} />
                        </CollapsibleSection>

                        <CollapsibleSection
                          count={reviewResult.contradictory_evidence.length}
                          defaultOpen={reviewResult.contradictory_evidence.length > 0}
                          title="Contradictory evidence"
                        >
                          <EvidenceCards items={reviewResult.contradictory_evidence} />
                        </CollapsibleSection>

                        <CollapsibleSection
                          count={reviewResult.missing_requirements.length}
                          defaultOpen={reviewResult.missing_requirements.length > 0}
                          title="Policy gaps"
                        >
                          <RequirementCards requirements={reviewResult.missing_requirements} />
                        </CollapsibleSection>

                        <CollapsibleSection count={reviewResult.satisfied_requirements.length} title="Satisfied policy requirements">
                          <RequirementCards compact requirements={reviewResult.satisfied_requirements} />
                        </CollapsibleSection>

                        <CollapsibleSection title="Evidence graph">
                          <EvidenceGraph graph={caseGraph} state={graphState} error={graphError} />
                        </CollapsibleSection>

                        <CollapsibleSection title="Agent workflow">
                          <WorkflowTrace steps={reviewResult.workflow_trace ?? []} />
                        </CollapsibleSection>

                        <CollapsibleSection count={reviewResult.graph_paths.length} title="Graph paths">
                          <div className="graph-paths">
                            {reviewResult.graph_paths.slice(0, 6).map((path, index) => (
                              <code key={`${path.source}-${path.relationship}-${path.target}-${index}`}>
                                {`${path.source} -> ${path.relationship} -> ${path.target}`}
                              </code>
                            ))}
                          </div>
                        </CollapsibleSection>
                      </div>
                    </section>
                  )}
                </>
              ) : (
                <div className="notice">Select a case to continue.</div>
              )}
            </article>

            <CollapsibleSection className="wide-panel" title="Audit history">
              <div className="panel-toolbar">
                <div>
                  <p className="eyebrow">Audit history</p>
                  <h3>Saved reviewer decisions</h3>
                </div>
                <button className="secondary-action" onClick={loadAuditRecords} type="button">
                  Refresh
                </button>
              </div>

              {auditState === "loading" && <div className="notice">Loading audit history...</div>}
              {auditState === "error" && (
                <div className="notice error">
                  <strong>Could not load audit history.</strong>
                  <span>{auditError}</span>
                </div>
              )}
              {auditState === "loaded" && (
                <div className="audit-list">
                  {auditRecords.length > 0 ? (
                    auditRecords.slice(0, 6).map((record) => <AuditCard key={record.audit_id} record={record} />)
                  ) : (
                    <p className="empty-state">No reviewer decisions saved yet.</p>
                  )}
                </div>
              )}
            </CollapsibleSection>

            <CollapsibleSection className="wide-panel" title="Evaluation">
              <div className="panel-toolbar">
                <div>
                  <p className="eyebrow">Evaluation</p>
                  <h3>Expected versus actual</h3>
                </div>
                <button className="secondary-action" onClick={loadEvaluation} type="button">
                  Run evaluation
                </button>
              </div>

              {evaluationState === "loading" && <div className="notice">Running evaluation...</div>}
              {evaluationState === "error" && (
                <div className="notice error">
                  <strong>Could not run evaluation.</strong>
                  <span>{evaluationError}</span>
                </div>
              )}
              {evaluationState === "loaded" && evaluation && (
                <>
                  <div className="evaluation-summary">
                    <div>
                      <span>Total cases</span>
                      <strong>{evaluation.total_cases}</strong>
                    </div>
                    <div>
                      <span>Passed</span>
                      <strong>{evaluation.passed_cases}</strong>
                    </div>
                    <div>
                      <span>Failed</span>
                      <strong>{evaluation.failed_cases}</strong>
                    </div>
                  </div>
                  <div className="evaluation-list">
                    {evaluation.cases.map((caseResult) => (
                      <EvaluationCard key={caseResult.case_id} result={caseResult} />
                    ))}
                  </div>
                </>
              )}
            </CollapsibleSection>
          </div>
        )}
      </section>
    </main>
  );
}

function EvaluationCard({ result }: { result: EvaluationSummary["cases"][number] }) {
  const checks: Array<[string, boolean]> = [
    ["Status", result.status_matches],
    ["Citations", result.citations_valid],
    ["Evidence recall", result.supporting_evidence_recall],
    ["Contradictions", result.contradictory_evidence_recall],
    ["Graph paths", result.graph_paths_present],
  ];

  return (
    <article className={`evaluation-card ${result.passed ? "passed" : "failed"}`}>
      <div className="evaluation-card-header">
        <div>
          <strong>{result.case_id}</strong>
          <span>{result.passed ? "Pass" : "Needs attention"}</span>
        </div>
        <span className={`result-badge ${result.actual_status}`}>{formatStatus(result.actual_status)}</span>
      </div>
      <dl className="evaluation-status-grid">
        <div>
          <dt>Expected</dt>
          <dd>{formatStatus(result.expected_status)}</dd>
        </div>
        <div>
          <dt>Actual</dt>
          <dd>{formatStatus(result.actual_status)}</dd>
        </div>
      </dl>
      <div className="evaluation-checks">
        {checks.map(([label, passed]) => (
          <span className={passed ? "passed" : "failed"} key={label}>
            {label}
          </span>
        ))}
      </div>
    </article>
  );
}

function CollapsibleSection({
  children,
  className = "",
  count,
  defaultOpen = false,
  title,
}: {
  children: ReactNode;
  className?: string;
  count?: number;
  defaultOpen?: boolean;
  title: string;
}) {
  return (
    <details className={`collapsible-section ${className}`} open={defaultOpen}>
      <summary>
        <span>{title}</span>
        <div>
          {typeof count === "number" && <small>{count}</small>}
          <ChevronDown size={16} aria-hidden="true" />
        </div>
      </summary>
      <div className="collapsible-body">{children}</div>
    </details>
  );
}

function EvidenceGraph({
  error,
  graph,
  state,
}: {
  error: string | null;
  graph: CaseGraph | null;
  state: GraphState;
}) {
  if (state === "loading") {
    return <div className="notice">Loading evidence graph...</div>;
  }

  if (state === "error") {
    return (
      <div className="notice error">
        <strong>Could not load graph.</strong>
        <span>{error}</span>
      </div>
    );
  }

  if (!graph) {
    return null;
  }

  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
  const visibleRelationships = graph.relationships.slice(0, 10);

  return (
    <section className="evidence-graph" aria-label="Evidence graph">
      <div className="evidence-graph-header">
        <span className="section-label">Evidence graph</span>
        <small>
          {graph.nodes.length} nodes · {graph.relationships.length} relationships
        </small>
      </div>
      <div className="graph-node-strip">
        {graph.nodes.slice(0, 12).map((node) => (
          <span className={`graph-node ${node.type}`} key={node.id}>
            {node.label}
          </span>
        ))}
      </div>
      <div className="graph-edge-list">
        {visibleRelationships.map((relationship, index) => (
          <div className="graph-edge" key={`${relationship.source}-${relationship.type}-${relationship.target}-${index}`}>
            <span>{nodesById.get(relationship.source)?.label ?? relationship.source}</span>
            <strong>{formatWorkflowStep(relationship.type)}</strong>
            <span>{nodesById.get(relationship.target)?.label ?? relationship.target}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function WorkflowTrace({ steps }: { steps: string[] }) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <section className="workflow-trace" aria-label="Workflow trace">
      <span className="section-label">Agent workflow</span>
      <ol>
        {steps.map((step, index) => (
          <li key={`${step}-${index}`}>
            <span>{index + 1}</span>
            <strong>{formatWorkflowStep(step)}</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}

function AuditCard({ record }: { record: AuditRecord }) {
  return (
    <article className={`audit-card ${record.reviewer_action}`}>
      <div className="audit-card-header">
        <div>
          <strong>{formatAction(record.reviewer_action)}</strong>
          <span>{record.case_id}</span>
        </div>
        <span className={`result-badge ${record.ai_status}`}>{formatStatus(record.ai_status)}</span>
      </div>
      <dl className="audit-card-meta">
        <div>
          <dt>Reviewer</dt>
          <dd>{record.reviewer_id}</dd>
        </div>
        <div>
          <dt>Decision time</dt>
          <dd>{formatDateTime(record.decided_at)}</dd>
        </div>
      </dl>
      {record.reviewer_comment && <p>{record.reviewer_comment}</p>}
      <small>Audit ID: {record.audit_id}</small>
    </article>
  );
}

function DecisionButton({
  action,
  disabled,
  label,
  onClick,
}: {
  action: ReviewerAction;
  disabled: boolean;
  label: string;
  onClick: (action: ReviewerAction) => void;
}) {
  return (
    <button className={`decision-button ${action}`} disabled={disabled} onClick={() => onClick(action)} type="button">
      {label}
    </button>
  );
}

function EvidenceCards({ items }: { items: EvidenceItem[] }) {
  return (
    <section className="evidence-section">
      {items.length > 0 ? (
        <div className="evidence-card-grid">
          {items.map((item) => (
            <article className="evidence-card" key={item.id}>
              <div className="evidence-card-header">
                <strong>{item.id}</strong>
                <span>{item.kind === "note" ? "Clinical note" : "Lab result"}</span>
              </div>
              <h5>{item.title}</h5>
              <div className="evidence-meta">
                <span>{item.date}</span>
                <span>{item.encounter_id}</span>
                {item.kind === "note" && <span>Page {item.page}</span>}
              </div>
              {item.kind === "note" ? (
                <>
                  <span className="evidence-section-name">{item.section}</span>
                  <p>{item.text}</p>
                </>
              ) : (
                <>
                  <p className="lab-value">
                    {item.value} {item.unit}
                  </p>
                  <p>{item.interpretation}</p>
                </>
              )}
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-state">None</p>
      )}
    </section>
  );
}

function RequirementCards({
  compact = false,
  requirements,
}: {
  compact?: boolean;
  requirements: PolicyRequirement[];
}) {
  return (
    <section className={`requirement-section ${compact ? "compact" : ""}`}>
      {requirements.length > 0 ? (
        <div className="requirement-grid">
          {requirements.map((requirement) => (
            <article className="requirement-card" key={requirement.id}>
              <strong>{requirement.id}</strong>
              <span>{requirement.label}</span>
              {!compact && <p>{requirement.description}</p>}
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-state">None</p>
      )}
    </section>
  );
}

function formatAction(action: ReviewerAction) {
  return action
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function formatStatus(status: ReviewResult["status"]) {
  return status
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function formatPacketTitle(caseId: string) {
  const match = caseId.match(/case_(\d+)/);
  return `Claim packet ${match?.[1] ?? caseId}`;
}

function formatWorkflowStep(step: string) {
  return step
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function formatModelMode(mode: string) {
  return mode
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default App;
