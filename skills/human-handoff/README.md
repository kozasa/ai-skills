# human-handoff

人間が短時間で理解・判断できる形式へ、エージェントの確認依頼や実装完了を整理するスキルです。

## 主な動作

- 短い事実や単純な質問は文章で返す
- 複数の判断や検証結果はFAST HTMLへ整理する
- review-loop後の非軽微な実装はImplementation Storyへ整理する
- 実画面取得にログインが必要なら、変更操作を触れる再構成HTMLへ切り替える
- 最終判断は人間へ残し、未確認事項を推測で埋めない

## 起動例

```text
$human-handoff story
```

Claude Codeでは `/human-handoff story`、自然言語では「このPRを実装ストーリーにまとめて」と依頼できます。

## 導入

`skills/human-handoff` を `~/.codex/skills/human-handoff` または `~/.claude/skills/human-handoff` へコピーしてください。Implementation Story生成には `quick-html` も導入します。

## ファイル構成

- `SKILL.md`: スキル本体
- `agents/openai.yaml`: Codex向け表示情報
