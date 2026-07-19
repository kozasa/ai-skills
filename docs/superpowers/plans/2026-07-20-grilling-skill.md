# Grilling Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable `grilling` skill that stress-tests plans one decision at a time, recommends an answer for every question, and finishes with a structured readiness verdict.

**Architecture:** The feature is a self-contained prompt skill under `skills/grilling/`. `SKILL.md` defines activation, the decision-tree interview, state management, research boundaries, and completion output; `README.md` and `agents/openai.yaml` provide human-facing and Codex-facing discovery. The root README adds the skill to the public catalog.

**Tech Stack:** Markdown skill instructions, YAML Codex interface metadata, POSIX shell validation, Git.

## Global Constraints

- The skill must be generic and must not depend on Kozasa-specific philosophy, private context, or repository conventions.
- Activation must require explicit grilling intent; ordinary planning requests alone must not trigger it.
- Ask exactly one decision question per turn and wait for the user's response.
- Every question must include a recommended answer and a short reason; add confidence when uncertain.
- Investigate discoverable facts before asking the user, and keep research read-only unless separately authorized.
- Maintain confirmed decisions, provisional assumptions, unresolved decisions, rejected alternatives, contradictions, and risks.
- Use no fixed question limit; completion depends on readiness criteria.
- Render the three readiness verdicts in the user's language.
- Do not add scripts, templates, references, automated test infrastructure, or changes to `review-loop`.

---

### Task 1: Implement the core grilling workflow

**Files:**
- Create: `skills/grilling/SKILL.md`

**Interfaces:**
- Consumes: explicit user intent such as `$grilling`, `grill this plan`, `grillして`, or a request to stress-test a plan before execution.
- Produces: one recommended decision question per turn, maintained decision state, and one localized readiness verdict plus the required final sections.

- [ ] **Step 1: Run the structural check and verify it fails before the skill exists**

Run:

```bash
test -f skills/grilling/SKILL.md \
  && rg -q '^name: grilling$' skills/grilling/SKILL.md \
  && rg -q 'exactly one decision question' skills/grilling/SKILL.md \
  && rg -q 'recommended answer' skills/grilling/SKILL.md \
  && rg -q 'Ready to execute' skills/grilling/SKILL.md
```

Expected: FAIL with a non-zero exit status because `skills/grilling/SKILL.md` does not exist.

- [ ] **Step 2: Create the minimal complete skill instructions**

Create `skills/grilling/SKILL.md` with this complete content:

```markdown
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
```

- [ ] **Step 3: Run the structural check and verify it passes**

Run:

```bash
test -f skills/grilling/SKILL.md \
  && rg -q '^name: grilling$' skills/grilling/SKILL.md \
  && rg -q 'exactly one decision question' skills/grilling/SKILL.md \
  && rg -q 'recommended answer' skills/grilling/SKILL.md \
  && rg -q 'Ready to execute' skills/grilling/SKILL.md \
  && rg -q 'provisional assumptions' skills/grilling/SKILL.md \
  && rg -q 'Do not silently reconcile conflicting answers' skills/grilling/SKILL.md
```

Expected: PASS with exit status 0 and no output.

- [ ] **Step 4: Check formatting and commit the core skill**

Run:

```bash
git diff --check
git add skills/grilling/SKILL.md
git commit -m "feat: add grilling workflow"
```

Expected: `git diff --check` produces no output; the commit succeeds and includes only `skills/grilling/SKILL.md`.

---

### Task 2: Add Codex discovery metadata

**Files:**
- Create: `skills/grilling/agents/openai.yaml`

**Interfaces:**
- Consumes: the `$grilling` skill name implemented in Task 1.
- Produces: Codex display name `Grilling`, a short description, and a default invocation prompt.

- [ ] **Step 1: Run the metadata check and verify it fails before the file exists**

Run:

```bash
test -f skills/grilling/agents/openai.yaml \
  && rg -q 'display_name: "Grilling"' skills/grilling/agents/openai.yaml \
  && rg -q '\$grilling' skills/grilling/agents/openai.yaml
```

Expected: FAIL with a non-zero exit status because the metadata file does not exist.

- [ ] **Step 2: Create the Codex interface metadata**

Create `skills/grilling/agents/openai.yaml` with:

```yaml
interface:
  display_name: "Grilling"
  short_description: "Stress-test a plan one decision at a time"
  default_prompt: "Use $grilling to stress-test this plan one decision at a time, recommend an answer for every question, and finish with an execution-readiness verdict."
```

- [ ] **Step 3: Run the metadata check and verify it passes**

Run:

```bash
test -f skills/grilling/agents/openai.yaml \
  && rg -q 'display_name: "Grilling"' skills/grilling/agents/openai.yaml \
  && rg -q 'short_description: "Stress-test a plan one decision at a time"' skills/grilling/agents/openai.yaml \
  && rg -q '\$grilling' skills/grilling/agents/openai.yaml
```

Expected: PASS with exit status 0 and no output.

- [ ] **Step 4: Check formatting and commit the metadata**

Run:

```bash
git diff --check
git add skills/grilling/agents/openai.yaml
git commit -m "feat: add grilling Codex metadata"
```

Expected: `git diff --check` produces no output; the commit succeeds and includes only `skills/grilling/agents/openai.yaml`.

---

### Task 3: Document installation and add the skill to the catalog

**Files:**
- Create: `skills/grilling/README.md`
- Modify: `README.md:7-10`

**Interfaces:**
- Consumes: the package paths and invocation name created in Tasks 1 and 2.
- Produces: public installation instructions for Codex and Claude Code plus a root-catalog link to `skills/grilling/`.

- [ ] **Step 1: Run the documentation check and verify it fails**

Run:

```bash
test -f skills/grilling/README.md \
  && rg -q '^# grilling$' skills/grilling/README.md \
  && rg -q '\[grilling\](skills/grilling/)' README.md
```

Expected: FAIL with a non-zero exit status because the skill README and root catalog entry do not exist.

- [ ] **Step 2: Create the skill README**

Create `skills/grilling/README.md` with:

````markdown
# grilling

計画や設計を実行する前に、一問ずつ厳しく検証するスキルです。重要な曖昧さ、矛盾、依存関係、未確認の前提、リスクを解消し、最後に実行可能性を判定します。

## 主な動作

- 質問は一度に一つだけ
- 各質問にAIの推奨回答と理由を提示
- コードや資料から確認できる内容は、ユーザーに聞かず先に調査
- 確定事項、仮説、未決事項、却下案、矛盾、リスクを継続管理
- 重大な未決事項がなくなるまで固定上限なしで深掘り
- 終了時に三段階の実行可否判定と合意内容を提示

技術・プロダクト設計、事業計画、業務フロー、講座設計、AIエージェント設計などに利用できます。実装やファイル変更は自動では行いません。

## 起動例

```text
$grilling この計画を実行前に詰めてください
```

次のような依頼でも起動できます。

```text
この事業計画をgrillして
重要な穴がなくなるまで一問ずつ質問して
Stress-test this design before implementation
```

単に「計画を相談したい」と伝えただけでは、長いヒアリングを避けるため自動起動しません。

## Codexへの導入

```bash
git clone git@github.com:kozasa/ai-skills.git
test ! -e ~/.codex/skills/grilling
mkdir -p ~/.codex/skills
cp -R ai-skills/skills/grilling ~/.codex/skills/grilling
```

既存の `~/.codex/skills/grilling` を更新する場合は、内容を確認してから置き換えてください。

## Claude Codeへの導入

Codexと同じ実体を共有する場合:

```bash
test ! -e ~/.claude/skills/grilling
mkdir -p ~/.claude/skills
ln -s ~/.codex/skills/grilling ~/.claude/skills/grilling
```

Claude Codeだけで使う場合は、`skills/grilling` を `~/.claude/skills/grilling` にコピーしてください。

## ファイル構成

- `SKILL.md`: スキル本体
- `agents/openai.yaml`: Codex向けの表示情報と起動プロンプト
````

- [ ] **Step 3: Add the root catalog row**

In `README.md`, change the skill table to:

```markdown
| Skill | 概要 |
|---|---|
| [grilling](skills/grilling/) | 計画や設計を一問ずつ厳しく検証し、実行可能な合意内容へ整理します。 |
| [review-loop](skills/review-loop/) | レビューと修正を反復し、人間向けの最終マージ判定を提示します。 |
```

- [ ] **Step 4: Run the documentation check and verify it passes**

Run:

```bash
test -f skills/grilling/README.md \
  && rg -q '^# grilling$' skills/grilling/README.md \
  && rg -q '\$grilling' skills/grilling/README.md \
  && rg -q 'Codexへの導入' skills/grilling/README.md \
  && rg -q 'Claude Codeへの導入' skills/grilling/README.md \
  && rg -q '\[grilling\](skills/grilling/)' README.md
```

Expected: PASS with exit status 0 and no output.

- [ ] **Step 5: Check formatting and commit the documentation**

Run:

```bash
git diff --check
git add README.md skills/grilling/README.md
git commit -m "docs: publish grilling skill"
```

Expected: `git diff --check` produces no output; the commit succeeds and contains the skill README and root README only.

---

### Task 4: Validate package integrity and behavior

**Files:**
- Verify: `skills/grilling/SKILL.md`
- Verify: `skills/grilling/README.md`
- Verify: `skills/grilling/agents/openai.yaml`
- Verify: `README.md`

**Interfaces:**
- Consumes: the complete package from Tasks 1-3.
- Produces: evidence that the package is structurally complete and that representative interactions follow the approved design.

- [ ] **Step 1: Verify the package contains only the approved files**

Run:

```bash
find skills/grilling -type f | sort
```

Expected output:

```text
skills/grilling/README.md
skills/grilling/SKILL.md
skills/grilling/agents/openai.yaml
```

- [ ] **Step 2: Run all static contract checks together**

Run:

```bash
test "$(find skills/grilling -type f | wc -l | tr -d ' ')" = 3 \
  && rg -q '^name: grilling$' skills/grilling/SKILL.md \
  && rg -q 'exactly one decision question' skills/grilling/SKILL.md \
  && rg -q 'recommended answer' skills/grilling/SKILL.md \
  && rg -q 'provisional assumptions' skills/grilling/SKILL.md \
  && rg -q 'Do not silently reconcile conflicting answers' skills/grilling/SKILL.md \
  && rg -q 'Ready to execute' skills/grilling/SKILL.md \
  && rg -q 'display_name: "Grilling"' skills/grilling/agents/openai.yaml \
  && rg -q '\[grilling\](skills/grilling/)' README.md \
  && git diff --check
```

Expected: PASS with exit status 0 and no output.

- [ ] **Step 3: Validate the activation boundary**

Run from the repository root:

```bash
codex exec --sandbox read-only 'Read skills/grilling/SKILL.md and decide whether it applies. The user says: "新規SaaSの計画を相談したい。" Return only the assistant response.'
```

Expected: the response does not enter a relentless grilling interview merely from the generic planning request; it may answer normally or offer grilling as an option.

- [ ] **Step 4: Validate research-before-asking behavior**

Run from the repository root:

```bash
codex exec --sandbox read-only 'Read skills/grilling/SKILL.md and follow it. The user says: "$grilling このリポジトリに新しいスキルを追加する計画を詰めて。最初の質問だけ返して。" You may inspect repository files.'
```

Expected: the response inspects the repository context, asks exactly one judgment question with a recommendation and reason, and does not ask which skills or package structure already exist.

- [ ] **Step 5: Validate a normal first grilling turn**

Run from the repository root:

```bash
codex exec --sandbox read-only 'Read skills/grilling/SKILL.md and follow it. The user says: "$grilling 新規SaaSの計画を詰めて。顧客は中小企業で、まず3か月以内に検証したい。" Return only your first response.'
```

Expected: the response asks exactly one decision question, includes a recommended answer and reason, and does not present a full plan or ask a list of questions.

- [ ] **Step 6: Validate delegated-answer and contradiction handling**

Run from the repository root:

```bash
codex exec --sandbox read-only 'Read skills/grilling/SKILL.md. Simulate the next response in this interview: the user first chose a one-month launch deadline, then said quality is the top priority and no scope may be reduced, and now says "任せる" when asked which constraint wins. Return only the assistant response.'
```

Expected: the response identifies the conflict, recommends a priority, treats delegation as provisional rather than confirmed, and asks exactly one resolution question.

- [ ] **Step 7: Validate the readiness gate**

Run from the repository root:

```bash
codex exec --sandbox read-only 'Read skills/grilling/SKILL.md. Produce the final output for a stopped interview where the purpose and target user are known, but pricing, owner, validation method, and launch constraints remain unresolved. Answer in Japanese.'
```

Expected: the first verdict is `実行前に追加検討が必要`; unresolved decisions are listed; the response does not claim `実行準備完了`.

- [ ] **Step 8: Review the final diff and history**

Run:

```bash
git status --short --branch
git diff main...HEAD --stat
git diff --check main...HEAD
git log --oneline main..HEAD
```

Expected:

- working tree is clean;
- the diff contains the design, implementation plan, `skills/grilling/` package, and root README entry only;
- `git diff --check` reports no errors;
- commits are small and purpose-specific.
