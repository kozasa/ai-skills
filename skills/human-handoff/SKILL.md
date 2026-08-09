---
name: human-handoff
description: Use when one or more agents need a human decision, confirmation, prioritization, or exception judgment, or when a complex completion report would be burdensome to understand as prose. Consolidate the human-relevant information and use fast local HTML when it materially reduces reading effort. Do not use for a short fact, one-line status, or an obvious yes/no question.
---

# Human Handoff

Present agent work so a human can understand and decide quickly. Choose the delivery format from the situation; version 1 uses ordinary prose or `$quick-html` FAST HTML.

## Workflow

1. Collect only the points the human needs to understand, decide, or verify.
2. Deduplicate overlapping questions from parallel agents without losing different consequences or owners.
3. Classify the event as `decision` or `completion`.
4. Compare formats:
   - Use **prose-only** for a short fact, one-line status, or obvious yes/no question with self-contained context.
   - Use FAST HTML when there are multiple decisions, alternatives, consequences, verification results, risks, or enough detail that scanning a page is faster than reading prose.
5. Build the normalized JSON contract below without inventing facts.
6. Save it to a local temporary JSON file and invoke `$quick-html` in FAST mode.
7. If rendering fails, return `title`, `summary`, `recommendation`, and `items` as concise Markdown and name the renderer failure.

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
