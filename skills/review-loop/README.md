# review-loop

実装完了後にレビュー、ブロッカーの修正、quality gatesを反復し、人間がマージ可否を判断しやすい形で結果を提示するスキルです。

## 主な動作

- 指摘をブロッカー、フォローアップ、提案の3段階に分類
- ブロッカーだけをフィックスし、フォローアップはBeadsへ移して追跡
- 各ラウンドでテスト・ビルド・リンタなどのquality gatesを実行
- 初回は変更全体、2回目以降は修正差分と影響範囲へレビューを限定
- フィックスはR1〜R5の最大5回
- R6は追加フィックスを行わない最終確認レビュー
- ループ内ではcommitしない
- Codexでは固定したdiffを空の一時ディレクトリのread-only新規インスタンスへ渡してレビュー
- 固定diffはmerge-base以降のbranch差分とHEAD以降の未コミット差分を分離し、base側だけの新規commitを逆向きの削除として扱わない
- 通常文脈10行、packetは1,000,000文字以下に制限し、Codexの入力上限超過を防止

## 最終マージ判定

結果の最上部に、次のいずれかを表示します。

- `マージ推奨`: ブロッカーとフォローアップ、失敗した必須gate、未確認の必須事項がない
- `条件付きマージ`: ブロッカーがなく必須gateが成功し、追跡済みのフォローアップや手動確認が残る
- `マージ非推奨`: ブロッカー、失敗した必須gate、またはブロッカーによる打ち切りがある

AIの判定は推奨であり、最終的なマージ判断は人間が行います。

## human-handoff 連携

この連携条件は **Codex / Claude Code 共通** です。

`マージ推奨` または `条件付きマージ` で終了し、`human-handoff` スキルが利用可能な場合は、
レビュー結果と人間の最終確認事項を handoff へ引き渡します。`マージ非推奨` では起動しません。

`~/.codex/skills/review-loop` に導入した場合、この動作は特定のプロジェクトに限定されず、
review-loop を起動したすべてのリポジトリに適用されます。各リポジトリへスキルを複製する
必要はありません。

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
- `scripts/codex_review.py`: Codex向けの独立・境界付きレビューランナー
- `tests/test_codex_review_runner.py`: ランナーの回帰テスト
- `tests/test_convergence_policy.py`: 収束方針の契約テスト
- `tests/test_human_handoff_contract.py`: handoff 発火条件の契約テスト
- `agents/openai.yaml`: Codex向けの表示情報と起動プロンプト
