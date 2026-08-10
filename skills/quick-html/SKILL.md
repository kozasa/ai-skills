---
name: quick-html
description: Use when creating a local HTML decision report, completion report, PR implementation story, or researched one-page explainer from normalized context, a topic, URL, or file path.
---

# quick-html

ユーザー入力 (topic 文字列 / URL / ファイルパス / 直前会話) を起点に、
**1 枚 HTML の図解付き解説ページ** を生成する orchestrator。

## Mode selection

処理開始前に必ずFAST、STORY、FULLのいずれかを決める。

- **FAST**: `--fast <input.json>`、または`type`が`decision` / `completion`の正規化JSON。`human-handoff`からは、明示的にFASTを指定した場合か、一時的でSTORYが過剰な例外時だけ選ぶ。
- **STORY**: `scripts/render_story.py --input <input.json> --output <index.html>`、PR後の実装経緯、または`human-handoff`の既定であるImplementation Story。
- **FULL**: 上記以外のトピック文字列、URL、ローカルファイルパス、または本格的な調査・AI画像付き解説の依頼。

曖昧な場合、既に十分なcontextがあり速度が目的ならFASTを選ぶ。追加調査や生成画像が成果物の価値に必要ならFULLを選ぶ。

## FAST mode

正規化JSONを、依存関係のない固定テンプレートで即座に1枚HTMLへ変換する。Do not run Phase 1 or Phase 3 in FAST mode.

入力契約は `scripts/render_fast.py` が検証する。実行例:

```bash
python3 <skill-dir>/scripts/render_fast.py \
  --input /absolute/path/to/input.json \
  --output "output/explainer-<slug>/index.html" \
  --open
```

- 調査エージェント、Web検索、AI画像、CDN、ビルド工程を使わない。
- 入力内容を補完・推測せず、足りない確証は未確認と明記した状態で渡す。
- rendererが失敗した場合は、`title`、`summary`、`recommendation`、`items` を簡潔なMarkdownで返し、HTML失敗を報告する。
- `--open` だけが失敗した場合もHTMLは生成済みなので、ローカルパスを返す。

## STORY mode

```bash
python3 <skill-dir>/scripts/render_story.py --input /absolute/story.json --output /absolute/implementation-story-<slug>/index.html
```

The complete contract example is `tests/human_handoff/fixtures/implementation-story/report.json`. Required roots are `slug`, `title`, `summary`, `at_a_glance`, `recommendation`, `decisions`, `implementation`, `visuals`, `flow`, `verification`, `constraints`, `next_actions`, and `references`. `hero_visual` and `pr_url` are optional.

- `at_a_glance`: `{what, why, how, human_decision}`. Keep each value to one to three short lines: what was done, why it was needed, how it was handled, and exactly what the human should confirm or decide.
- `hero_visual`: optional `{path, alt, caption}` for the handoff's ImageGen illustration. Use a safe relative 16:9 PNG path; the renderer verifies the PNG signature and aspect ratio. Render it directly below the title and before `at_a_glance`.
- `pr_url`: optional https URL of the pull request. It renders as a prominent PRを開く button at the top right of the header so the human can open the PR immediately; always set it when a PR exists.
- `recommendation.status`: `merge-recommended`, `conditional`, or `do-not-merge`. A blocking verification not marked `passed` forbids `merge-recommended`. `human_checks` renders as 人間が見る点 in the emphasized left column of 判断概要.
- `decisions`: may be an empty array when the agent made no discretionary judgment; the page then states that explicitly. Never invent a decision to fill the section.
- `implementation`: each item requires `importance` (`high`, `medium`, or `low`). The renderer sorts items high→low and shows a 重要度: 大/中/小 badge, so list what matters most and grade it honestly.
- Page order: header with optional PRを開く button（右上）→ optional ImageGen hero → HTML overview（変更の要点と確認事項）→ 視覚的な証拠 → 処理フロー → 判断概要 → 重要な判断 → 実装されたもの（1カラム）→ verification/actions → references.
- A reconstructed preview must display `コードから再構成した操作デモ`, use fictional data, include `aria-live`, and make no 外部通信. Embed it with `sandbox="allow-scripts"`.
- Draw `flow.diagram_path` in standard flowchart notation — rectangles for steps, `shape: diamond` for decisions. The default is a D2 sketch diagram converted with `scripts/d2_to_svg.py --input flow.d2 --output diagrams/<name>.svg` (runs the `d2` CLI in sketch mode and pre-validates the SVG; requires `brew install d2`). Color-code node roles with D2 classes: decisions `fill "#fdf3d8"` / `stroke "#b08a2e"`, normal outcomes `fill "#e3f0e3"` / `stroke "#35633d"`, waits and errors `fill "#f7e3e0"` / `stroke "#963830"`. Write multi-line labels with `\n` inside quoted strings — never `|md` blocks, which emit foreignObject and fail validation. When the `d2` CLI is unavailable, fall back to a Mermaid flowchart via `scripts/mermaid_to_svg.py --input flow.mmd --output diagrams/<name>.svg` (wraps `npx @mermaid-js/mermaid-cli` with `securityLevel: strict` and `htmlLabels: false`). Both provide a ローカルSVG; do not load D2, Mermaid, or a CDN at viewing time. When a diagram is present the HTML flow steps render as a collapsed テキスト版フロー; they stay visible only as the last-resort fallback when no SVG is available.
- Never invent a screen, link, test result, or recommendation. Mark unavailable evidence honestly.
- Default output is `output/implementation-story-<slug>/index.html`; do not commit it unless asked.

## FULL mode

FULL と判定したら、作業開始前に `references/full-mode.md` を必ず読む。Input/Output 契約、Phase 1〜5 (Research subagent fan-out / Outline 設計 / 画像 fan-out / HTML 組み立て / open) の全手順、fork 縮退モード、Gotchas、テンプレート情報はすべてそこに集約されている。記憶だけで FULL を実行しない。FAST / STORY では読まない。
