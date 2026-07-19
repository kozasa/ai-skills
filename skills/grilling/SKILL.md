---
name: grilling
description: Use when the user explicitly asks to grill, stress-test, or rigorously clarify a plan or design before execution; triggers include "$grilling", "grill this plan", "grillして", "この計画を詰めて", and requests to ask questions until important gaps are resolved.
---

# Grilling

## Purpose

Stress-test a plan or design before execution. Resolve material ambiguity, contradictions, dependencies, assumptions, and risks through a rigorous but non-aggressive interview.

Use this for technical designs, product plans, business initiatives, operating procedures, course designs, and AI-agent designs. Do not use it for simple factual lookup, review of a completed artifact, or implementation itself.

## Activation Boundary

Start only when the user expresses explicit grilling or stress-testing intent. A generic request to discuss or create a plan is not sufficient by itself because this workflow can be lengthy.

## Research Before Questions

Before asking, inspect relevant conversation context, code, documents, configuration, and existing decisions. Do not ask the user for information available through those sources.

When a decision depends on changing external facts such as pricing, law, product specifications, competitors, or market conditions, verify them with available sources. Cite important factual claims with an absolute verification date. Mark anything that cannot be verified as unverified.

Keep research read-only. Do not modify files, publish, change sharing settings, send internal information externally, or write to connected services unless the user separately authorizes it.

## Interview Rules

1. Ask exactly one decision question per turn, then wait for the answer.
   One question means one independently answerable decision. Do not hide multiple requested details, subquestions, or checklist items under one top-level question. A prompt to fill multiple fields is multiple questions even when grouped into one sentence or template. Ask for one choice or approval only; infer or defer every dependent detail to separate later turns. After the one question, recommendation, reason, and optional confidence, end the turn; do not append requests for evidence, corrections, examples, elaboration, or additional details.
2. Resolve the current decision-tree branch before opening another branch.
3. With every question, provide:
   - the recommended answer;
   - a short reason;
   - a confidence label when uncertain.
4. Challenge the plan, not the user. Be direct about ambiguity, unsupported assumptions, contradictions, hidden dependencies, unclear success criteria, and missing failure handling without becoming hostile.
5. Show only the state change relevant to the current question. Give a brief intermediate summary when a branch closes; do not repeat the full state after every answer.

Cover these areas in dependency order when they apply:

1. purpose and background;
2. success criteria;
3. target users and usage context;
4. scope and explicit exclusions;
5. constraints and priorities;
6. core components, behavior, and operations;
7. dependencies;
8. failure modes and risks;
9. validation method;
10. execution, rollout, migration, and completion conditions.

Mark a non-applicable area as such with a reason instead of forcing irrelevant questions.

## State

Maintain:

- confirmed decisions;
- provisional assumptions;
- unresolved decisions;
- rejected alternatives and reasons;
- contradictions;
- risks and validation items.

If the user says they do not know or delegates the decision, adopt the recommendation as a provisional assumption. Revisit it when it materially affects a later decision.

Do not silently reconcile conflicting answers. Identify the conflicting decisions and their practical impact, then ask exactly one question about which takes priority. Allow earlier decisions to change and record the reason.

## Completion

Use no fixed question limit. Propose completion only when:

- purpose and success criteria are clear;
- scope and exclusions are clear;
- major dependencies and decisions are resolved;
- material risks and failure responses are understood;
- no important ambiguity remains that would make an executor guess.

The user may stop at any time. On early termination, still produce the final output and preserve unresolved items.

## Final Output

Start with exactly one verdict, rendered in the user's language:

- `Ready to execute` / `実行準備完了`: no material unresolved decision remains.
- `Conditionally executable` / `条件付きで実行可能`: explicit assumptions or follow-up verification remain, but work can safely begin under stated conditions.
- `More design work required` / `実行前に追加検討が必要`: a material decision or blocker remains unresolved.

Then provide:

1. Purpose and success criteria
2. Confirmed decisions
3. Constraints and exclusions
4. Provisional assumptions
5. Risks and mitigations
6. Unresolved decisions
7. Rejected alternatives and reasons
8. Recommended next action

Never use the `Ready to execute` state while a material unresolved decision or unverified critical assumption remains.
