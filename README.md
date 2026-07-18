# ai-skills

kozasaが管理する、Codex / Claude Code向けの再利用可能なAIエージェントスキル集です。

## Skills

### review-loop

実装完了後にレビュー、high指摘の修正、quality gatesを反復し、最終的に人間向けのマージ推奨判定を出します。

- フィックス最大5回＋R6確認レビュー
- high指摘のみ修正し、low指摘は見送り事項として記録
- 各ラウンドでquality gatesを実行
- `マージ推奨` / `条件付きマージ` / `マージ非推奨` をレポート最上部に表示
- ループ内ではcommitしない

起動例:

```text
$review-loop
```

## Install for Codex

```bash
git clone git@github.com:kozasa/ai-skills.git
test ! -e ~/.codex/skills/review-loop
mkdir -p ~/.codex/skills
cp -R ai-skills/skills/review-loop ~/.codex/skills/review-loop
```

既存の `~/.codex/skills/review-loop` を更新する場合は、内容を確認してから置き換えてください。

## Install for Claude Code

Codexと同じ実体を共有する場合:

```bash
test ! -e ~/.claude/skills/review-loop
mkdir -p ~/.claude/skills
ln -s ~/.codex/skills/review-loop ~/.claude/skills/review-loop
```

Claude Codeだけで使う場合は、`skills/review-loop` を `~/.claude/skills/review-loop` にコピーしてください。
