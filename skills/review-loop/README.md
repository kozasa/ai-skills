# review-loop

実装完了後にレビュー、high指摘の修正、quality gatesを反復し、人間がマージ可否を判断しやすい形で結果を提示するスキルです。

## 主な動作

- high指摘のみをフィックスし、low指摘は見送り事項として記録
- 各ラウンドでテスト・ビルド・リンタなどのquality gatesを実行
- フィックスはR1〜R5の最大5回
- R6は追加フィックスを行わない最終確認レビュー
- ループ内ではcommitしない

## 最終マージ判定

結果の最上部に、次のいずれかを表示します。

- `マージ推奨`: high指摘、失敗した必須gate、未確認の必須事項がない
- `条件付きマージ`: high指摘はないが、手動確認や未実行の必須gateが残る
- `マージ非推奨`: high指摘、失敗した必須gate、または打ち切りがある

AIの判定は推奨であり、最終的なマージ判断は人間が行います。

## 起動

```text
$review-loop
```

## Codexへの導入

```bash
git clone git@github.com:kozasa/ai-skills.git
test ! -e ~/.codex/skills/review-loop
mkdir -p ~/.codex/skills
cp -R ai-skills/skills/review-loop ~/.codex/skills/review-loop
```

既存の `~/.codex/skills/review-loop` を更新する場合は、内容を確認してから置き換えてください。

## Claude Codeへの導入

Codexと同じ実体を共有する場合:

```bash
test ! -e ~/.claude/skills/review-loop
mkdir -p ~/.claude/skills
ln -s ~/.codex/skills/review-loop ~/.claude/skills/review-loop
```

Claude Codeだけで使う場合は、`skills/review-loop` を `~/.claude/skills/review-loop` にコピーしてください。

## ファイル構成

- `SKILL.md`: スキル本体
- `agents/openai.yaml`: Codex向けの表示情報と起動プロンプト
