---
name: human-handoff
description: Use when one or more agents need a human decision, confirmation, prioritization, or exception judgment; when a complex completion report would be burdensome as prose; or after review-loop and PR creation when a human needs to recover implementation context.
---

# Human Handoff

Present agent work so a human can understand and decide quickly. Default to Implementation Story whenever the handoff contains enough context to deserve a generated artifact.

## Workflow

1. Collect only the points the human needs to understand, decide, or verify.
2. Deduplicate overlapping questions from parallel agents without losing different consequences or owners.
3. Use prose only for a short fact, one-line status, or obvious yes/no question whose context is fully self-contained.
4. Default to Implementation Story for decisions, completion reports, review handoffs, PR context, or any report with background, consequences, verification, risks, or follow-up actions.
5. Build the STORY contract from `$quick-html` without inventing facts.
6. Save it to a local JSON file and invoke `$quick-html` in STORY mode.
7. If rendering fails, return the STORY content as concise Markdown, name the renderer failure, and preserve Story First order.

Do not reply to child agents, choose on the user's behalf, or automate the user's response. Do not delay an urgent decision for presentation work; fall back to concise prose when that is faster.

## Implementation Story

Keep Story First: judgment summary, background/request, Story, decisions, and implementation stay before visual evidence. The Story explains causality; evidence confirms it.

Begin every STORY contract with `at_a_glance: {what, why, how}`. Keep each value to roughly one to three lines: `what` states the delivered outcome, `why` states the problem that caused the work, and `how` states the essential implementation approach. Do not merely repeat the title or replace concrete facts with vague summary language.

Collect evidence in this order: authentication-free existing preview, automatically started local UI, usable existing signed-in session, interactive reconstructed HTML, then static explanation. If obtaining a screen requires 人間のログイン, credentials, or manual environment preparation, stop that attempt and use 再構成HTML. Never increase human work merely to obtain a screenshot.

Reconstructed previews must say `コードから再構成した操作デモ` and use fictional data with no external communication. Reproduce the changed operation and state transitions, not the complete appearance. Label actual, screenshot, and reconstructed evidence honestly.

Give an evidence-backed recommendation, but 最終判断は人間. Do not use `merge-recommended` if any blocking verification has not passed. Render with `$quick-html` STORY mode under `output/implementation-story-<slug>/`; do not commit generated output unless asked.
