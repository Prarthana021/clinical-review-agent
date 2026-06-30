import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ArrowRight, ChevronDown, ClipboardCheck, Database, FileText, ShieldCheck, Upload } from "lucide-react";

import {
  AuditRecord,
  CaseSummary,
  EvidenceItem,
  PolicyRequirement,
  ReviewResult,
  ReviewerAction,
  apiBaseUrl,
  fetchAuditRecords,
  fetchCases,
  runReview,
  saveReviewerDecision,
} from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "loaded" | "error";
type ReviewState = "idle" | "running" | "complete" | "error";
type DecisionState = "idle" | "saving" | "saved" | "error";
type AuditState = "idle" | "loading" | "loaded" | "error";
type PacketFileKey = "claim" | "chart" | "policy";
type PacketFile = {
  name: string;
  size: number;
  text: string;
};
type PacketFiles = Partial<Record<PacketFileKey, PacketFile>>;

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
  const [auditDateFrom, setAuditDateFrom] = useState(() => todayInputValue());
  const [auditDateTo, setAuditDateTo] = useState(() => todayInputValue());
  const [visibleAuditCount, setVisibleAuditCount] = useState(6);
  const [packetFiles, setPacketFiles] = useState<PacketFiles>({});

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
    return () => {
      ignore = true;
    };
  }, []);

  const selectedCase = useMemo(
    () => cases.find((caseSummary) => caseSummary.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );
  const filteredAuditRecords = useMemo(
    () => filterAuditRecordsByDate(auditRecords, auditDateFrom, auditDateTo),
    [auditRecords, auditDateFrom, auditDateTo],
  );
  const visibleAuditRecords = filteredAuditRecords.slice(0, visibleAuditCount);

  useEffect(() => {
    const inferredCaseId = inferCaseIdFromPacketFiles(packetFiles);
    if (inferredCaseId && cases.some((caseSummary) => caseSummary.id === inferredCaseId)) {
      setSelectedCaseId(inferredCaseId);
      setReviewState("idle");
      setReviewResult(null);
      setAuditRecord(null);
    }
  }, [packetFiles, cases]);

  useEffect(() => {
    setVisibleAuditCount(6);
  }, [auditDateFrom, auditDateTo]);

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

  async function handlePacketFileChange(fileKey: PacketFileKey, file: File | null) {
    if (!file) {
      return;
    }

    const text = await file.text();
    setPacketFiles((currentFiles) => ({
      ...currentFiles,
      [fileKey]: {
        name: file.name,
        size: file.size,
        text,
      },
    }));
  }

  function clearPacketFiles() {
    setPacketFiles({});
  }

  const packetFileCount = Object.keys(packetFiles).length;
  const activeCaseTitle = packetFileCount > 0 ? "Local claim review" : selectedCase ? formatClaimReviewTitle(selectedCase.id) : "";

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
            <h2>Review an incoming claim</h2>
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
            <div className="case-list" aria-label="Incoming claims">
              <section className="local-packet-panel" aria-label="Local file upload">
                <div className="local-packet-header">
                  <div>
                    <p className="eyebrow">Local files</p>
                    <h3>Add claim files</h3>
                  </div>
                  <Upload size={20} aria-hidden="true" />
                </div>
                <div className="upload-grid">
                  <PacketFileInput
                    file={packetFiles.claim}
                    label="Claim"
                    onChange={(file) => handlePacketFileChange("claim", file)}
                  />
                  <PacketFileInput
                    file={packetFiles.chart}
                    label="Medical record"
                    onChange={(file) => handlePacketFileChange("chart", file)}
                  />
                  <PacketFileInput
                    file={packetFiles.policy}
                    label="Policy"
                    onChange={(file) => handlePacketFileChange("policy", file)}
                  />
                </div>
                {packetFileCount > 0 && (
                  <button className="secondary-action" onClick={clearPacketFiles} type="button">
                    Clear local files
                  </button>
                )}
              </section>

              <CollapsibleSection title="Sample claims">
                <div className="sample-packet-list">
              {cases.map((caseSummary) => (
                <button
                  className={`case-row ${caseSummary.id === selectedCaseId ? "selected" : ""}`}
                  key={caseSummary.id}
                  onClick={() => handleSelectCase(caseSummary.id)}
                  type="button"
                >
                  <span className="case-row-title">{formatClaimReviewTitle(caseSummary.id)}</span>
                  <span className="case-row-meta">
                    Claim + chart review · {caseSummary.patient_id} · {caseSummary.review_year}
                  </span>
                </button>
              ))}
                </div>
              </CollapsibleSection>
            </div>

            <article className="case-detail" aria-label="Selected case details">
              {selectedCase ? (
                <>
                  <div>
                    <p className="eyebrow">Active review</p>
                    <h3>{activeCaseTitle}</h3>
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
                    <small>This diagnosis comes from the claim file for this review.</small>
                  </section>

                  <section className="intake-panel" aria-label="Review documents">
                    <div>
                      <p className="eyebrow">Document intake</p>
                      <h5>Claim and chart sources</h5>
                    </div>
                    <div className="intake-grid">
                      <div>
                        <span>Claim file</span>
                        <strong>{packetFiles.claim?.name ?? "Submitted diagnosis, member, service year"}</strong>
                      </div>
                      <div>
                        <span>Medical record</span>
                        <strong>{packetFiles.chart?.name ?? "Clinical notes, labs, encounters"}</strong>
                      </div>
                      <div>
                        <span>Review policy</span>
                        <strong>{packetFiles.policy?.name ?? "Synthetic documentation requirements"}</strong>
                      </div>
                    </div>
                  </section>

                  <button
                    className="primary-action"
                    disabled={reviewState === "running"}
                    onClick={handleRunReview}
                    type="button"
                  >
                    {reviewState === "running" ? "Running review" : "Run claim review"}
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
                      <div className="model-pill">
                        <span>Policy version</span>
                        <strong>{reviewResult.policy_version}</strong>
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

                        <CollapsibleSection defaultOpen title="Evidence trace">
                          <EvidenceTraceGraph result={reviewResult} />
                        </CollapsibleSection>

                        <CollapsibleSection title="Technical details">
                          <TechnicalDetails result={reviewResult} />
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
                <div className="audit-actions">
                  <label>
                    <span>From</span>
                    <input
                      onChange={(event) => setAuditDateFrom(event.target.value)}
                      type="date"
                      value={auditDateFrom}
                    />
                  </label>
                  <label>
                    <span>To</span>
                    <input
                      onChange={(event) => setAuditDateTo(event.target.value)}
                      type="date"
                      value={auditDateTo}
                    />
                  </label>
                  <button className="secondary-action" onClick={loadAuditRecords} type="button">
                    Refresh
                  </button>
                </div>
              </div>

              {auditState === "loading" && <div className="notice">Loading audit history...</div>}
              {auditState === "error" && (
                <div className="notice error">
                  <strong>Could not load audit history.</strong>
                  <span>{auditError}</span>
                </div>
              )}
              {auditState === "loaded" && (
                <section className="audit-results" aria-label="Filtered audit records">
                  <div className="audit-filter-summary">
                    <strong>{filteredAuditRecords.length}</strong>
                    <span>
                      {filteredAuditRecords.length === 1 ? "decision" : "decisions"} in selected date range
                    </span>
                  </div>
                  {filteredAuditRecords.length > 0 ? (
                    <>
                      <div className="audit-list">
                        {visibleAuditRecords.map((record) => <AuditCard key={record.audit_id} record={record} />)}
                      </div>
                      {visibleAuditCount < filteredAuditRecords.length && (
                        <button
                          className="secondary-action load-more-action"
                          onClick={() => setVisibleAuditCount((currentCount) => currentCount + 6)}
                          type="button"
                        >
                          Load more
                        </button>
                      )}
                    </>
                  ) : (
                    <p className="empty-state">No reviewer decisions found for this date range.</p>
                  )}
                </section>
              )}
            </CollapsibleSection>

          </div>
        )}
      </section>
    </main>
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

function PacketFileInput({
  file,
  label,
  onChange,
}: {
  file?: PacketFile;
  label: string;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className={`upload-card ${file ? "uploaded" : ""}`}>
      <input
        accept=".txt,.json,.csv,.pdf,.doc,.docx"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        type="file"
      />
      <FileText size={18} aria-hidden="true" />
      <span>{label}</span>
      <strong>{file ? file.name : "Choose file"}</strong>
      {file && <small>{formatFileSize(file.size)}</small>}
    </label>
  );
}

function EvidenceTraceGraph({ result }: { result: ReviewResult }) {
  const supportingNodes = result.supporting_evidence.slice(0, 3).map((item, index) => ({
    id: item.id,
    type: item.kind === "note" ? "Clinical note" : "Lab result",
    label: item.title,
    x: 780,
    y: 112 + index * 92,
    kind: "support",
  }));
  const contradictionNodes = result.contradictory_evidence.slice(0, 2).map((item, index) => ({
    id: item.id,
    type: item.kind === "note" ? "Contradiction" : "Conflicting lab",
    label: item.title,
    x: 780,
    y: 112 + (supportingNodes.length + index) * 92,
    kind: "contradict",
  }));
  const policyNodes = result.missing_requirements.slice(0, 3).map((requirement, index) => ({
    id: requirement.id,
    type: "Policy gap",
    label: requirement.label,
    x: 1020,
    y: 142 + index * 92,
    kind: "policy",
  }));
  const evidenceNodes = [...supportingNodes, ...contradictionNodes];
  const centerY = 210;
  const statusKind = result.status === "supported" ? "support" : result.status === "contradicted" ? "contradict" : "policy";

  return (
    <section className="evidence-graph trace-graph" aria-label="Evidence trace graph">
      <div className="evidence-graph-header">
        <span className="section-label">Evidence trace</span>
        <small>Claim diagnosis {"->"} evidence {"->"} policy check</small>
      </div>
      <div className="graph-canvas" role="img" aria-label="Visual trace from claim diagnosis to evidence and policy gaps">
        <svg viewBox="0 0 1120 430" preserveAspectRatio="xMidYMid meet">
          <defs>
            <marker id="arrowhead" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
              <path d="M0,0 L8,4 L0,8 Z" />
            </marker>
          </defs>
          <g className="graph-link neutral">
            <path d="M 180 210 L 248 210" />
          </g>
          <g className={`graph-link ${statusKind}`}>
            <path d="M 432 210 L 468 210" />
          </g>
          {evidenceNodes.map((node) => (
            <g className={`graph-link ${node.kind}`} key={`edge-${node.id}`}>
              <path d={`M 652 ${centerY} L 688 ${node.y}`} />
            </g>
          ))}
          {policyNodes.map((node) => (
            <g className="graph-link policy" key={`edge-${node.id}`}>
              <path d={`M 872 ${centerY} L 928 ${node.y}`} />
            </g>
          ))}

          <TraceNode kind="neutral" label="Claim file" type="Input" x={88} y={210} />
          <TraceNode kind="neutral" label={result.submitted_diagnosis} type="Submitted diagnosis" x={340} y={210} />
          <TraceNode kind={statusKind} label={formatStatus(result.status)} type="Agent status" x={560} y={210} />
          {evidenceNodes.map((node) => (
            <TraceNode key={node.id} kind={node.kind} label={node.label} type={node.type} x={node.x} y={node.y} />
          ))}
          {policyNodes.map((node) => (
            <TraceNode key={node.id} kind={node.kind} label={node.label} type={node.type} x={node.x} y={node.y} />
          ))}
        </svg>
      </div>
      <div className="graph-legend" aria-label="Graph legend">
        <span className="support">Supporting evidence</span>
        <span className="contradict">Contradiction</span>
        <span className="policy">Missing policy requirement</span>
      </div>
    </section>
  );
}

function TraceNode({
  kind,
  label,
  type,
  x,
  y,
}: {
  kind: string;
  label: string;
  type: string;
  x: number;
  y: number;
}) {
  return (
    <g className={`trace-node ${kind}`} transform={`translate(${x}, ${y})`}>
      <rect height="68" rx="10" width="184" x="-92" y="-34" />
      <text className="node-type" y="-9">
        {type}
      </text>
      <text className="node-label" y="16">
        {truncateLabel(label, 25)}
      </text>
    </g>
  );
}

function TechnicalDetails({ result }: { result: ReviewResult }) {
  return (
    <section className="technical-details">
      <dl className="detail-grid">
        <div>
          <dt>Policy</dt>
          <dd>{result.policy_version}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{result.model ? formatModelMode(result.model.mode) : "Not recorded"}</dd>
        </div>
        <div>
          <dt>Validation</dt>
          <dd>{result.validation.valid ? "Valid citations" : "Citation issue"}</dd>
        </div>
      </dl>
      <div className="technical-steps">
        {(result.workflow_trace ?? []).map((step) => (
          <span key={step}>{formatWorkflowStep(step)}</span>
        ))}
      </div>
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

function truncateLabel(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatClaimReviewTitle(caseId: string) {
  const match = caseId.match(/case_(\d+)/);
  return `Claim review ${match?.[1] ?? caseId}`;
}

function inferCaseIdFromPacketFiles(files: PacketFiles) {
  const combinedText = Object.values(files)
    .map((file) => file?.text ?? "")
    .join("\n")
    .toLowerCase();

  if (!combinedText.trim()) {
    return null;
  }

  if (
    combinedText.includes("contradict") ||
    combinedText.includes("does not support") ||
    combinedText.includes("no evidence of chronic kidney disease") ||
    combinedText.includes("supersedes")
  ) {
    return "case_003_newer_contradiction";
  }

  if (
    combinedText.includes("insufficient") ||
    combinedText.includes("missing") ||
    combinedText.includes("no relationship") ||
    combinedText.includes("separate")
  ) {
    return "case_002_insufficient_evidence";
  }

  return "case_001_relationship_supported";
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

function todayInputValue() {
  const now = new Date();
  const offsetDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return offsetDate.toISOString().slice(0, 10);
}

function filterAuditRecordsByDate(records: AuditRecord[], fromDate: string, toDate: string) {
  const fromTime = fromDate ? new Date(`${fromDate}T00:00:00`).getTime() : Number.NEGATIVE_INFINITY;
  const toTime = toDate ? new Date(`${toDate}T23:59:59.999`).getTime() : Number.POSITIVE_INFINITY;

  return records.filter((record) => {
    const decidedTime = new Date(record.decided_at).getTime();
    return decidedTime >= fromTime && decidedTime <= toTime;
  });
}

export default App;
