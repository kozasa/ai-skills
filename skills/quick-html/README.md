# quick-html

正規化済みの判断依頼・完了報告・実装経緯を、依存関係のないローカルHTMLへ変換するスキルです。

## モード

- FAST: 判断依頼と完了報告を1枚HTMLへ変換
- STORY: Story Firstの説明、触れる再構成HTML、ローカルSVG、検証結果をImplementation Storyへ変換
- FULL: 調査や画像生成を含む本格的な解説ページ

STORY modeは外部通信を許可せず、HTML、相対JavaScript module、CSS、画像、ローカル画面遷移、参照資料を入力ルート内で安全に同梱します。

## 起動例

```bash
python3 skills/quick-html/scripts/render_story.py \
  --input /absolute/path/to/story.json \
  --output output/implementation-story-example/index.html
```

## 導入

`skills/quick-html` を `~/.codex/skills/quick-html` または `~/.claude/skills/quick-html` へコピーしてください。

## ファイル構成

- `SKILL.md`: orchestratorと入力契約
- `scripts/render_fast.py`: FAST renderer
- `scripts/render_story.py`: STORY renderer
- `templates/`: ローカルHTMLテンプレート
- `agents/openai.yaml`: Codex向け表示情報
