# AI and Graph Plan

## Purpose

The AI and graph layer will retrieve connected evidence, apply deterministic policy rules, validate citations, and generate a plain-language explanation for the reviewer.

## Core Principle

The graph and deterministic policy rules decide the system status. The language model explains the result.

MedGemma should not be the sole authority for whether a case is supported, contradicted, or requires expert review.

## GraphRAG Goal

The graph must distinguish:

- A diagnosis submitted on a claim.
- Individual clinical conditions documented in the chart.
- A required relationship between conditions.
- Evidence that supports or contradicts the relationship.
- Evidence that is current, outdated, copied, or superseded.
- Policy requirements satisfied by each evidence item.

## Main Diagnosis

Submitted diagnosis:

**Type 2 diabetes mellitus with chronic kidney disease stage 3**

The system must check:

- Diabetes documentation.
- CKD stage 3 documentation.
- Relationship evidence between diabetes and CKD.
- Current review-period evidence.
- Active assessment, monitoring, evaluation, or treatment.
- Newer contradictory or superseding evidence.

## Important Rule

Separate documentation does not automatically mean the relationship is unsupported.

The system should focus on:

- Explicit unrelated statements.
- Outdated relationship evidence.
- Missing current evidence.
- Missing policy-required assessment or management.
- Newer contradictions.
- Superseding notes.

## Agentic Workflow

Planned conditional paths:

- Missing evidence -> search again.
- Contradiction found -> run conflict analysis.
- Invalid citations -> retry explanation generation once.
- Still unresolved -> escalate to human.
- Model unavailable -> use cached explanation.

## MVP Implementation Order

1. Use prepared JSON graph data.
2. Implement in-memory graph traversal.
3. Add deterministic status rules.
4. Add citation validation.
5. Add cached AI explanations.
6. Add Neo4j adapter only after the local graph flow works.
7. Add live MedGemma only after cached mode works.

