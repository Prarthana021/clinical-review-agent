# Demo Cases Plan

## Purpose

The demo uses three controlled synthetic cases to prove that Clinical Review Agent can find support, avoid overclaiming when evidence is incomplete, and identify contradictions.

## Shared Submitted Diagnosis

**Type 2 diabetes mellitus with chronic kidney disease stage 3**

## Case 1: Relationship Supported

Situation:

- A current clinical note explicitly connects diabetes and CKD stage 3.
- A relevant eGFR lab supports CKD.
- The note includes monitoring or management.

Expected AI status:

`supported`

## Case 2: Missing Relationship or Management Evidence

Situation:

- Diabetes is documented.
- CKD stage 3 is documented.
- A relevant eGFR lab supports CKD.
- The current record does not contain policy-satisfying relationship evidence or active management evidence.

Expected AI status:

`insufficient_evidence`

Important:

This case is not insufficient merely because the two conditions appear in separate notes. The issue is missing policy-required evidence in the prepared synthetic record.

## Case 3: Newer Contradiction

Situation:

- Older evidence supports the submitted diagnosis.
- A newer specialist note contradicts active CKD stage 3 or supersedes the older support.

Expected AI status:

`contradicted`

## MVP Completion Criteria

All three cases must:

- Produce the expected AI status.
- Retrieve the correct evidence.
- Have zero invalid citations.
- Display a graph path.
- Save the reviewer decision.
- Work in cached fallback mode.

Expected results should be hidden during the main demo and shown only on the evaluation page.

