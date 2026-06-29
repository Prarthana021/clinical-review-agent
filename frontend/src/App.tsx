import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, ClipboardCheck, Database, ShieldCheck } from "lucide-react";

import { CaseSummary, fetchCases } from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "loaded" | "error";

function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadCases() {
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

    loadCases();
    return () => {
      ignore = true;
    };
  }, []);

  const selectedCase = useMemo(
    () => cases.find((caseSummary) => caseSummary.id === selectedCaseId) ?? null,
    [cases, selectedCaseId],
  );

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
          <div className="status-pill">
            <Activity size={16} aria-hidden="true" />
            Backend connected
          </div>
        </header>

        {loadState === "loading" && <div className="notice">Loading case queue...</div>}
        {loadState === "error" && (
          <div className="notice error">
            <strong>Could not load cases.</strong>
            <span>{error}</span>
          </div>
        )}

        {loadState === "loaded" && (
          <div className="case-layout">
            <div className="case-list" aria-label="Available cases">
              {cases.map((caseSummary) => (
                <button
                  className={`case-row ${caseSummary.id === selectedCaseId ? "selected" : ""}`}
                  key={caseSummary.id}
                  onClick={() => setSelectedCaseId(caseSummary.id)}
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

                  <button className="primary-action" type="button" disabled>
                    Start review
                    <ArrowRight size={17} aria-hidden="true" />
                  </button>
                  <p className="helper-text">Review execution will be connected in the next frontend slice.</p>
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

export default App;

