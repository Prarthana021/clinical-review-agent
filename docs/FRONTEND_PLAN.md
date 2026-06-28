# Frontend Plan

## Purpose

The frontend will provide a reviewer workspace for selecting synthetic cases, running the review, inspecting evidence, and saving a human decision.

## Initial Stack

- React
- TypeScript
- Vite
- Tailwind CSS or Material UI
- React Flow for graph visualization later

## First Frontend Slice

After the backend case loader exists, build a simple case-selection screen:

- List the three synthetic cases.
- Show the submitted diagnosis.
- Let the user select a case.
- Do not show expected results in the main demo flow.

## Main Screens

### 1. Case Selection

Displays:

- Case title.
- Patient summary.
- Submitted diagnosis.
- Start review button.

Expected results should stay hidden here.

### 2. Review Workspace

Displays:

- Patient and claim summary.
- AI review status.
- Supporting evidence.
- Contradictory evidence.
- Missing requirements.
- Policy checklist.
- Graph path.
- Reviewer action buttons.

Reviewer actions:

- Approve.
- Reject.
- Request Documentation.
- Escalate.

### 3. Evaluation and Audit

Displays:

- Expected result.
- Actual result.
- Citation validation status.
- Reviewer decision.
- Audit timestamp.

Expected versus actual belongs here only.

## Design Rule

The UI should feel like a practical reviewer tool, not a marketing page. Prioritize clear evidence, readable status, and fast reviewer action.

