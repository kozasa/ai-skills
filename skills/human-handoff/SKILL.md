---
name: human-handoff
description: Use when one or more agents need a human decision, confirmation, prioritization, or exception judgment; when a complex completion report would be burdensome as prose; or after review-loop and PR creation when a human needs to recover implementation context.
---

# Human Handoff

Present agent work so a human can understand and decide quickly. Choose prose, `$quick-html` FAST HTML, or an Implementation Story.

## Workflow

1. Collect only the points the human needs to understand, decide, or verify.
2. Deduplicate overlapping questions from parallel agents without losing different consequences or owners.
3. Classify the event as `decision`, `completion`, or `implementation-story`.
4. Compare formats:
   - Use **prose-only** for a short fact, one-line status, or obvious yes/no question with self-contained context.
   - Use FAST HTML when there are multiple decisions, alternatives, consequences, verification results, risks, or enough detail that scanning a page is faster than reading prose.
   - Use Implementation Story after `review-loop` and PR creation for non-trivial work.
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

Keep Story First: judgment summary, background/request, Story, decisions, and implementation stay before visual evidence. The Story explains causality; evidence confirms it.

Collect evidence in this order: authentication-free existing preview, automatically started local UI, usable existing signed-in session, interactive reconstructed HTML, then static explanation. If obtaining a screen requires 人間のログイン, credentials, or manual environment preparation, stop that attempt and use 再構成HTML. Never increase human work merely to obtain a screenshot.

Reconstructed previews must say `コードから再構成した操作デモ` and use fictional data with no external communication. Reproduce the changed operation and state transitions, not the complete appearance. Label actual, screenshot, and reconstructed evidence honestly.

Give an evidence-backed recommendation, but 最終判断は人間. Do not use `merge-recommended` if any blocking verification has not passed. Render with `$quick-html` STORY mode under `output/implementation-story-<slug>/`; do not commit generated output unless asked.
