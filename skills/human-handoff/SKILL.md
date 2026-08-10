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

Begin every Implementation Story with a short visual overview. Build `at_a_glance` as `{what, why, how, human_decision}` and keep each value to one to three lines. Show `やったこと → なぜ必要か → どう対応したか → 確認してほしいこと`. Write a concrete action in `human_decision`; do not use vague wording such as `確認してください` alone.

Use Implementation Story with this overview when any of these is true: there are at least three material changes, multiple components or roles are affected, causality is difficult to follow in prose, a human decision is required, or review/PR history is substantial. Continue to use prose-only or FAST for the exceptions in the workflow.

Keep Story First: optional ImageGen hero, HTML overview, judgment summary, background/request, Story, decisions, and implementation stay before visual evidence. ImageGen provides the first intuitive impression; the HTML overview is the accurate map; the Story explains causality; evidence confirms it.

### ImageGen for important handoffs

Use the HTML overview for every Implementation Story. Add one ImageGen illustration only when the user marks the handoff important or when at least two of these apply: customer/public impact, difficult-to-reverse or high-risk change, multiple teams or roles, executive-level judgment, or long-lived reference value.

Use Codex ImageGen to create a 16:9 `infographic-diagram` that explains the central causal relationship or operating model. The image must be understandable without reading the surrounding article. Save the selected raster image inside the handoff output source tree, add it as `hero_visual: {path, alt, caption}`, and render it directly below the title and before `at_a_glance`.

Write the image specification with exact, short Japanese text for all five elements below. Prefer five to ten Japanese characters per label and five to seven labels total; do not replace them with generic English.

1. A conclusion-led title that says what the diagram proves.
2. A label for every major step or object.
3. A short condition on every decision branch.
4. A concrete outcome at every endpoint.
5. One takeaway sentence at the bottom.

Use this prompt shape:

```text
Text (verbatim):
- Title: "<結論が分かる日本語>"
- Steps: "<工程1>" / "<工程2>" / "<工程3>"
- Branches: "<条件A>" / "<条件B>"
- Outcomes: "<結果A>" / "<結果B>"
- Takeaway: "<一行結論>"
Constraints: render every quoted Japanese label clearly; no unexplained icons; no English substitution.
```

After generation, inspect the image itself. Reject and regenerate once when any required label is missing, unreadable, garbled, too small, or replaced by English, or when icons and arrows do not make the causal direction clear. For a bridge retry to the same output path, add `--replace`; replacement is atomic and occurs only after the new PNG passes signature verification. If the second result still fails, omit ImageGen and use an HTML/CSS explanatory figure; never accept an attractive but semantically unclear image.

- In Codex, use `$imagegen` and its built-in ImageGen tool.
- In Claude Code or another runtime without Codex ImageGen, first reduce the content to a non-sensitive visual specification. Do not include customer data, personal information, credentials, private source text, or internal identifiers. Save that specification to a local prompt file, then run `scripts/generate-with-codex-imagegen.sh --prompt-file <path> --output <handoff-source>/images/<name>.png`. This invokes `codex exec` ephemerally with the workspace-write sandbox and returns a verified PNG.
- If the bridge, authentication, or image generation fails, continue with the HTML overview. Do not switch to an API-key-based image generator or expose secrets.

Do not delay or fail a handoff because image generation is unavailable. Omit `hero_visual`, keep the HTML overview, and state the omission only when it matters to the human decision.

Collect evidence in this order: authentication-free existing preview, automatically started local UI, usable existing signed-in session, interactive reconstructed HTML, then static explanation. If obtaining a screen requires 人間のログイン, credentials, or manual environment preparation, stop that attempt and use 再構成HTML. Never increase human work merely to obtain a screenshot.

Reconstructed previews must say `コードから再構成した操作デモ` and use fictional data with no external communication. Reproduce the changed operation and state transitions, not the complete appearance. Label actual, screenshot, and reconstructed evidence honestly.

Give an evidence-backed recommendation, but 最終判断は人間. Do not use `merge-recommended` if any blocking verification has not passed. Render with `$quick-html` STORY mode under `output/implementation-story-<slug>/`; do not commit generated output unless asked.
