---
name: human-handoff
description: Use when one or more agents need a human decision, confirmation, prioritization, or exception judgment; when a complex completion report would be burdensome as prose; or after review-loop and PR creation when a human needs to recover implementation context.
---

# Human Handoff

Present agent work so a human can understand and decide quickly. Default to an Implementation Story; use prose or `$quick-html` FAST HTML only for the exceptions below.

## Workflow

1. Collect only the points the human needs to understand, decide, or verify.
2. Deduplicate overlapping questions from parallel agents without losing different consequences or owners.
3. Classify the event as `implementation-story` by default. Use `decision` or `completion` only when an exception below clearly applies.
4. Choose the format:
   - Use **Implementation Story** for the default handoff, including non-trivial decisions and completion reports. It does not require a completed `review-loop` or an existing PR.
   - Use **prose-only** only for a short fact, one-line status, an urgent interruption, or an obvious yes/no question with self-contained context.
   - Use FAST HTML only when the user explicitly requests FAST, or when the handoff is transient and the full STORY contract would add disproportionate work without improving the human decision.
5. Build the matching normalized contract without inventing facts: the FAST contract below for `decision` or `completion`, and the STORY contract from `$quick-html` for `implementation-story`.
6. Save it to a local JSON file and invoke `$quick-html` in FAST or STORY mode as classified.
7. If rendering fails, return the matching normalized content as concise Markdown and name the renderer failure. Preserve Story First order for an Implementation Story.

Do not reply to child agents, choose on the user's behalf, or automate the user's response. Do not delay an urgent decision for presentation work; fall back to concise prose when that is faster.

## FAST input contract

Use this exact shape:

```json
{
  "type": "decision",
  "slug": "agent-confirmations",
  "title": "確認したいこと",
  "summary": "3件の判断が必要です。",
  "recommendation": "推奨案を上から確認してください。",
  "items": [
    {
      "title": "公開範囲",
      "body": "社内限定を推奨します。",
      "status": "recommended"
    }
  ],
  "details": [
    {
      "title": "判断材料",
      "body": "外部公開には追加レビューが必要です。"
    }
  ],
  "sources": [
    {
      "label": "設計書",
      "url": "docs/design.md"
    }
  ]
}
```

Required string fields are `type`, `slug`, `title`, and `summary`.

- `type`: exactly `decision` or `completion`.
- `slug`: lowercase kebab-case.
- `recommendation`: optional string; omit it when no evidence-backed recommendation exists.
- `items`: optional array of `{title, body, status}`; status is `recommended`, `warning`, or `neutral`.
- `details`: optional array of `{title, body}`.
- `sources`: optional array of `{label, url}`. Keep local paths local and do not externalize internal data.

Label uncertainty in the content. Never fill a missing recommendation merely to make the page look complete.

## Invocation

Pass the local JSON file to `$quick-html --fast`. Its installed `scripts/render_fast.py` owns validation, escaping, templating, output creation, and optional browser opening. Do not reproduce the HTML template in this skill.

For a normal repository, write the result under `output/explainer-<slug>/index.html`. If that would modify a repository for a transient confirmation, use an operating-system temporary directory instead.

## Implementation Story

STORY 契約のフィールド定義・必須項目・ページ順序は `$quick-html` の STORY mode 節が正本。ここには handoff 固有の判断だけを書く。

Begin every Implementation Story with a short visual overview. Build `at_a_glance` as `{what, why, how, human_decision}` and show `やったこと → なぜ必要か → どう対応したか → 確認してほしいこと`. Write a concrete action in `human_decision`; do not use vague wording such as `確認してください` alone.

Use Implementation Story with this overview when any of these is true: there are at least three material changes, multiple components or roles are affected, causality is difficult to follow in prose, a human decision is required, or review/PR history is substantial. Continue to use prose-only or FAST for the exceptions in the workflow.

Keep Story First: ImageGen hero, HTML overview, visual evidence, and flow stay before the judgment summary, decisions, and implementation. ImageGen provides the first intuitive impression; the HTML overview is the accurate map; evidence and flow show what was actually built before the reader reaches the judgment.

Handoff 固有の強調点:

- `pr_url`: when a PR already exists, always set its https URL so the page shows a PRを開く button at the top right; the human opens the PR from there. Omit it when there is no PR yet.
- `recommendation.human_checks`: list concrete checks, one action each.
- `decisions`: list only judgments the agent made at its own discretion where an alternative existed, so the human can overturn them. State what was decided and why. Leave the array empty when no such judgment exists; never invent one.

### ImageGen hero image

Every Implementation Story needs an opening image (イメージ). Generate one ImageGen illustration per story by default; before generating, read `references/imagegen-hero.md` for the image specification, prompt shape, inspection criteria, and runtime-specific invocation. When image generation is unavailable or fails twice, fall back to an HTML/CSS explanatory figure instead.

Do not delay or fail a handoff because image generation is unavailable. Omit `hero_visual`, keep the HTML overview, and state the omission only when it matters to the human decision.

Collect evidence in this order: authentication-free existing preview, automatically started local UI, usable existing signed-in session, interactive reconstructed HTML, then static explanation. If obtaining a screen requires 人間のログイン, credentials, or manual environment preparation, stop that attempt and use 再構成HTML. Never increase human work merely to obtain a screenshot.

Reconstructed previews must say `コードから再構成した操作デモ` and use fictional data with no external communication. Reproduce the changed operation and state transitions, not the complete appearance. Label actual, screenshot, and reconstructed evidence honestly.

Give an evidence-backed recommendation, but 最終判断は人間. Do not use `merge-recommended` if any blocking verification has not passed. Render with `$quick-html` STORY mode under `output/implementation-story-<slug>/`; do not commit generated output unless asked.
