# quick-html

入力された文脈から、1枚のHTML解説ページを生成するスキルです。

## モード

- **FAST**: 正規化済みJSONを、外部依存なしでローカルHTMLへ変換します。
- **FULL**: トピック、URL、ローカルファイルをもとに、調査や図解を含む本格的な解説ページを作ります。
- **STORY**: 背景・依頼・判断・実装・結果を、Story FirstのローカルHTMLにまとめます。

`human-handoff`から呼ばれる場合、短い事実や自明な質問以外はSTORYを既定にします。通常案件は冒頭にHTML図解、重要案件はさらにCodex ImageGenの説明図をタイトル直下へ追加します。

## STORY冒頭の構成

- 「やったこと」を全幅で大きく表示
- その下に「なぜ必要か」「どう対応したか」「確認してほしいこと」を3カラムで表示
- 重要案件のImageGen画像には、日本語のタイトル、流れ、分岐条件、結果、要点を画像内へ明記

STORYは相対JavaScript module、別画面、CSS、画像を入力ルート内で再帰的に解決し、外部通信なしのローカル資産として同梱します。

## インストール

ルートの [README](../../README.md) にあるCodex / Claude Code共通の手順を使ってください。

## 直接試す

完全な入力例は `tests/human_handoff/fixtures/implementation-story/report.json` にあります。

```bash
python3 ~/.codex/skills/quick-html/scripts/render_story.py \
  --input /absolute/path/to/report.json \
  --output /tmp/implementation-story-sample/index.html \
  --open
```

Claude Code側だけへ導入した場合は、パスを `~/.claude/skills/quick-html/` に読み替えてください。
