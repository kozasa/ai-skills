---
name: human-handoff
description: Use when one or more agents need a human decision, confirmation, prioritization, or exception judgment; when a complex completion report would be burdensome as prose; or after review-loop and PR creation when a human needs to recover an implementation's background, request, decisions, result, and evidence.
---

# Human Handoff

Present agent work so a human can understand and decide quickly. Choose ordinary prose, `$quick-html` FAST HTML, or an Implementation Story from the situation.

## Workflow

1. Collect only the points the human needs to understand, decide, or verify.
2. Deduplicate overlapping questions from parallel agents without losing different consequences or owners.
3. Classify the event as `decision`, `completion`, or `implementation-story`.
4. Compare formats:
   - Use **prose-only** for a short fact, one-line status, or obvious yes/no question with self-contained context.
   - Use FAST HTML when there are multiple decisions, alternatives, consequences, verification results, risks, or enough detail that scanning a page is faster than reading prose.
   - Use **Implementation Story** after `review-loop` and PR creation when the human needs the PRの経緯: background, original request, important decisions, implementation, actual screen or structural evidence, verification, and references.
5. Build the matching normalized JSON contract without inventing facts.
6. Save it to a local JSON file and invoke `$quick-html` in FAST or Implementation Story mode.
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

## Implementation Story

Trigger when the user says「実装ストーリーを作って」「このPRの経緯をHTMLでまとめて」「このセッションの成果物を見える化して」or asks for a post-PR human handoff. Prefer automatic use after `review-loop` and PR creation for non-trivial work.

Collect only evidence available in the current session, local Git checkout, and accessible PR/review metadata. Synthesize the causal story instead of copying the chat log or entire diff. Mark inferred or unavailable evidence honestly.

Pass the normalized JSON described by `$quick-html` to `scripts/render_story.py`.

- Inside a repository: default to `output/implementation-story-<slug>/index.html` and do not commit unless explicitly asked.
- Outside a repository: accept a PR URL, repository path, or current-session context. Use an OS temporary directory for transient output, or `~/Documents/implementation-stories/<slug>/index.html` when the user asks to keep it.
- For UI work, include a safe relative preview or screenshot when available. For non-UI work, use flow, diff, or verification evidence only when it improves understanding.
- Do not claim a check passed without execution evidence. Use `unverified` when evidence is absent.
