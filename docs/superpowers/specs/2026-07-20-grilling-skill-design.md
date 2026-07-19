# Grilling Skill Design

## Summary

`grilling` is a reusable Codex and Claude Code skill that stress-tests a plan or design before execution. It resolves important ambiguities, contradictions, dependencies, and risks through a strict one-question-at-a-time interview. It is rigorous without being hostile and gives a recommended answer with every question.

The skill produces a structured agreement and an execution-readiness verdict. It does not implement the plan, edit project files, or save a design document unless the user separately requests those actions.

## Goals

- Help users turn incomplete plans and designs into executable decisions.
- Ask only questions that require human judgment.
- Investigate facts that can be discovered from available code, documents, configuration, conversation context, or external sources.
- Resolve one branch of the decision tree before moving to another.
- Make contradictions and unverified assumptions explicit.
- End with a concise artifact that another person or agent can use without rereading the interview.

## Non-goals

- Simple factual lookup.
- Review of an already completed artifact or implementation.
- Implementation, file modification, publication, or external sharing.
- Automatic creation or persistence of a specification.
- Automatic activation for every planning conversation.

## Intended Uses

The skill is generic and may be used for:

- technical and product design;
- business plans and initiatives;
- operating procedures and workflows;
- course and educational-product design;
- AI agent and automation design.

It must not depend on Kozasa-specific philosophy, private context, or repository conventions.

## Activation

Activation is explicit-intent-first. Examples include:

- `$grilling`;
- `grill this plan`;
- `grillして` or `この計画を詰めて`;
- `ask me questions until there are no important gaps`;
- `stress-test this before execution`.

A generic request such as `help me plan this` or `I want to discuss an idea` is insufficient by itself because the interview can be lengthy and demanding.

## Interaction Model

### Stance

The agent is rigorous but not aggressive. It challenges ambiguity, unsupported assumptions, contradictions, hidden dependencies, unclear success criteria, and missing failure handling. It criticizes the plan rather than the user.

### One question at a time

The agent asks exactly one decision question per turn and waits for the answer. It must not bundle related questions into a list. If a topic needs multiple decisions, it asks them in dependency order across separate turns.

Every question includes:

1. the decision being requested;
2. the agent's recommended answer;
3. a short reason;
4. a confidence label when the recommendation is uncertain.

### Research before asking

The agent must not ask the user for information it can discover from available context or tools. Before asking a question, it checks relevant conversation history, code, documents, configuration, and existing decisions.

When the plan depends on changing external facts such as pricing, law, product specifications, competitors, or market conditions, the agent verifies those facts using available sources. Important factual claims include a source and absolute verification date. Unverifiable claims are marked `unverified` and are not silently treated as facts.

Research is read-only by default. Sending internal information externally, modifying files, publishing, changing sharing settings, or writing to connected services requires separate user authorization.

## Decision-tree Flow

The interview uses a required coverage checklist with dynamic ordering. Dependencies determine the actual sequence, and the agent resolves the current branch before opening another.

Required coverage areas are:

1. purpose and background;
2. success criteria;
3. target users and usage context;
4. scope and explicit exclusions;
5. constraints and priorities;
6. core components, behavior, and operations;
7. dependencies;
8. failure modes and risks;
9. validation method;
10. execution, rollout, migration, and completion conditions when applicable.

Areas that clearly do not apply may be marked not applicable with a reason rather than discussed artificially.

## State Model

The agent maintains these categories throughout the conversation:

- confirmed decisions;
- provisional assumptions;
- unresolved decisions;
- rejected alternatives and reasons;
- contradictions;
- risks and validation items.

The agent normally shows only the change relevant to the current question. When a branch closes, it gives a brief intermediate summary. It avoids repeating the entire state after every answer.

### Delegated or unknown answers

If the user replies with `I don't know`, `you decide`, or an equivalent response, the agent adopts its recommendation as a provisional assumption rather than blocking. It revisits that assumption when it materially affects a later decision.

### Contradictions

The agent must not silently reconcile conflicting answers. It identifies the two conflicting decisions, explains the practical impact, and asks one question about which should take priority. Earlier decisions may be changed, and the reason for the change is recorded.

## Completion

There is no fixed question limit. The agent may propose completion when all of the following are true:

- purpose and success criteria are clear;
- scope and exclusions are clear;
- major dependencies and decisions are resolved;
- material risks and failure responses are understood;
- no important ambiguity remains that would cause an executor to guess.

The user may stop the interview at any time. Early termination still produces the final output and explicitly lists unresolved decisions.

## Final Output

The final output starts with exactly one readiness verdict, rendered in the user's language:

- `Ready to execute` / `実行準備完了`: no material unresolved decision remains;
- `Conditionally executable` / `条件付きで実行可能`: explicit assumptions or follow-up verification remain, but work can safely begin under stated conditions;
- `More design work required` / `実行前に追加検討が必要`: a material decision or blocker remains unresolved.

The remainder contains:

1. purpose and success criteria;
2. confirmed decisions;
3. constraints and exclusions;
4. provisional assumptions;
5. risks and mitigations;
6. unresolved decisions;
7. rejected alternatives and reasons;
8. recommended next action.

The verdict must follow from the recorded state. The agent must not report the `Ready to execute` state while a material unresolved decision or unverified critical assumption remains.

## Package Structure

The repository addition follows the existing `review-loop` convention:

```text
skills/grilling/
├── README.md
├── SKILL.md
└── agents/
    └── openai.yaml
```

- `SKILL.md` contains activation, interview rules, state handling, completion rules, and final-output requirements.
- `README.md` explains purpose, examples, and installation for Codex and Claude Code.
- `agents/openai.yaml` provides the Codex display name, short description, and default prompt.
- The repository root `README.md` adds `grilling` to the skill table.

No `references/`, `scripts/`, or templates are required for the initial version. They should be added only when the core instructions can no longer remain concise and self-contained.

## Validation Scenarios

The implementation will be checked against representative conversations that verify:

- only one question is asked per turn;
- every question includes a recommendation and reason;
- discoverable facts are investigated instead of asked;
- decision branches are completed without jumping unpredictably between topics;
- delegated answers become provisional assumptions;
- contradictions are surfaced and explicitly resolved;
- early termination retains unresolved items;
- the `Ready to execute` state is withheld when a material gap remains;
- explicit grilling intent activates the skill;
- ordinary planning requests do not cause over-eager activation;
- the final output contains every required section and one valid readiness verdict.

## Implementation Boundary

This design covers one self-contained skill package and the root README entry. It does not introduce scripts, tool-specific integrations, automated test infrastructure, or changes to `review-loop`.
