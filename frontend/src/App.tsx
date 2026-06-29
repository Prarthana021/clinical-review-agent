import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, ClipboardCheck, Database, ShieldCheck } from "lucide-react";

import {
  AuditRecord,
  CaseSummary,
  ReviewResult,
  ReviewerAction,
  apiBaseUrl,
  fetchCases,
  runReview,
  saveReviewerDecision,
} from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "loaded" | "error";
type ReviewState = "idle" | "running" | "complete" | "error";
type DecisionState = "idle" | "saving" | "saved" | "error";

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
    return () => {
      ignore = true;
    };
  }, []);

  const selectedCase = useMemo(
    () => cases.find((caseSummary) => caseSummary.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );

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
            <h1>Reviewer case queue</h1>
          </div>
        </div>

        <section className="metric-group" aria-label="Workflow overview">
          <div className="metric-item">
            <ClipboardCheck size={18} aria-hidden="true" />
            <span>Claim diagnosis intake</span>
          </div>
          <div className="metric-item">
            <Database size={18} aria-hidden="true" />
            <span>Graph evidence retrieval</span>
          </div>
          <div className="metric-item">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Human final action</span>
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
            <h2>Choose a synthetic claim for review</h2>
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
            <div className="case-list" aria-label="Available cases">
              {cases.map((caseSummary) => (
                <button
                  className={`case-row ${caseSummary.id === selectedCaseId ? "selected" : ""}`}
                  key={caseSummary.id}
                  onClick={() => handleSelectCase(caseSummary.id)}
                  type="button"
                >
                  <span className="case-row-title">{caseSummary.title}</span>
                  <span className="case-row-meta">
                    {caseSummary.patient_id} · Review year {caseSummary.review_year}
                  </span>
                </button>
              ))}
            </div>

            <article className="case-detail" aria-label="Selected case details">
              {selectedCase ? (
                <>
                  <div>
                    <p className="eyebrow">Selected case</p>
                    <h3>{selectedCase.title}</h3>
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
                  </section>

                  <button
                    className="primary-action"
                    disabled={reviewState === "running"}
                    onClick={handleRunReview}
                    type="button"
                  >
                    {reviewState === "running" ? "Running review" : "Start review"}
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

                      <div className="result-grid">
                        <EvidenceList title="Supporting evidence" values={reviewResult.supporting_evidence_ids} />
                        <EvidenceList title="Contradictory evidence" values={reviewResult.contradictory_evidence_ids} />
                        <EvidenceList title="Missing requirements" values={reviewResult.missing_requirement_ids} />
                      </div>

                      <div className="graph-paths">
                        <span className="section-label">Graph paths</span>
                        {reviewResult.graph_paths.slice(0, 6).map((path, index) => (
                          <code key={`${path.source}-${path.relationship}-${path.target}-${index}`}>
                            {`${path.source} -> ${path.relationship} -> ${path.target}`}
                          </code>
                        ))}
                      </div>

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
                          <div className="audit-confirmation">
                            <span>Audit saved</span>
                            <strong>{formatAction(auditRecord.reviewer_action)}</strong>
                            <small>Audit ID: {auditRecord.audit_id}</small>
                          </div>
                        )}
                      </section>
                    </section>
                  )}
                </>
              ) : (
                <div className="notice">Select a case to continue.</div>
              )}
            </article>
          </div>
        )}
      </section>
    </main>
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

function EvidenceList({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="result-list">
      <span className="section-label">{title}</span>
      {values.length > 0 ? (
        <ul>
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <p>None</p>
      )}
    </div>
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

export default App;
