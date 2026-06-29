# Clinical Review Agent Demo Script

Use this flow for a short hackathon demo. Keep the focus on the working proof of concept: graph evidence retrieval, deterministic validation, cached explanation fallback, and human review.

## 1. Start The App

Terminal 1:

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Open the frontend URL shown by Vite.

## 2. Opening Position

Say:

> Clinical Review Agent is a synthetic payer-side review copilot. It does not make final clinical, coding, payment, or compliance decisions. It prepares evidence-cited review packages so a human reviewer can approve, reject, request documentation, or escalate.

Point out:

- The data is synthetic.
- The submitted diagnosis is Type 2 diabetes mellitus with chronic kidney disease stage 3.
- The important graph problem is whether the chart supports the diabetes-CKD relationship, not just whether both words appear somewhere.

## 3. Show The Case Queue

Show the three cases:

- `001 Relationship Supported`
- `002 Insufficient Evidence`
- `003 Newer Contradiction`

Explain:

- Case 1 proves the happy path.
- Case 2 proves the system can avoid over-approving when relationship evidence is missing.
- Case 3 proves the system can surface newer contradictory evidence.

## 4. Run The Contradiction Case

Select:

```text
003 Newer Contradiction
```

Click:

```text
Start review
```

Show:

- AI status: `Contradicted`
- Explanation source: `Cached Fallback`
- Agent workflow steps:
  - Load Case
  - Retrieve Graph Evidence
  - Apply Deterministic Rules
  - Conflict Analysis
  - Generate Model Explanation
  - Citation Validation

Say:

> The model did not choose this status. The deterministic graph and policy rules classified the case. The explanation layer only turns the rule result into reviewer-friendly language.

## 5. Show Evidence

Point to:

- Supporting evidence from older nephrology documentation.
- Contradictory evidence from newer specialist or primary-care documentation.
- Missing policy requirements, if any.
- Satisfied policy requirements.

Say:

> The reviewer does not have to search every page manually. The package organizes the exact evidence and identifies where the chart conflicts.

## 6. Show The Evidence Graph

Point to:

- Submitted diagnosis node.
- Condition nodes.
- Relationship node.
- Clinical note and lab nodes.
- Policy requirement nodes.
- Contradiction or superseding relationships.

Say:

> This is why GraphRAG matters. The graph distinguishes separate condition mentions from an explicit relationship and can show newer evidence that contradicts older support.

## 7. Save A Human Decision

In the reviewer action area:

1. Add a short comment:

```text
Newer documentation conflicts with the submitted diagnosis. Requesting additional review.
```

2. Click:

```text
Request Documentation
```

Show:

- Audit saved message.
- Audit history card.

Say:

> The final action is still human-controlled. The system records the evidence, rule result, explanation source, validation result, and reviewer decision.

## 8. Show Evaluation

Scroll to:

```text
Evaluation
```

Click:

```text
Run evaluation
```

Show:

- Total cases: `3`
- Passed: `3`
- Failed: `0`
- Expected versus actual status for all cases.

Say:

> Expected results are hidden from the main review screen and only shown in the evaluation section, so the demo does not look hardcoded during the reviewer workflow.

## 9. Close

Say:

> This POC proves that connected patient evidence can be retrieved, validated against synthetic policy rules, explained, and presented to a human reviewer more clearly than isolated document search. The current version uses prepared graph data and cached model explanations for reliability. The architecture is ready for live MedGemma and Neo4j integration as follow-up work.

## Backup API Checks

If the frontend has an issue, use:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/cases
curl http://127.0.0.1:8000/evaluation
curl http://127.0.0.1:8000/cases/case_003_newer_contradiction/graph
```
