# run-explainer-page

入力された文脈から、1枚の HTML 解説ページを生成するスキルです。

## モード

- **FAST**: 人間向けの確認依頼・完了報告を、調査や画像生成なしで即座にローカル HTML へ変換します。
- **FULL**: トピック、URL、ローカルファイルをもとに、調査や図解を含む本格的な解説ページを作ります。

`human-facing-communication` から呼ばれる場合は FAST モードを使います。

## FAST モードの特徴

- Python 3 の標準ライブラリだけで動作
- npm / pip install、CDN、ビルド工程が不要
- 外部通信なし
- 入力値を HTML エスケープ
- 1ファイルの HTML を生成
- 結論をタイトル直下とページ末尾の両方に表示

## インストール

ルートの [README](../../README.md) にある Codex / Claude Code 共通の手順を使ってください。

## FAST モードを直接試す

入力 JSON を用意します。

```json
{
  "type": "decision",
  "slug": "publish-scope",
  "title": "公開範囲の確認",
  "summary": "公開前に1件の判断が必要です。",
  "recommendation": "最初は社内限定で公開することを推奨します。",
  "items": [
    {
      "title": "社内限定",
      "body": "フィードバックを集めてから外部公開します。",
      "status": "recommended"
    }
  ]
}
```

次のコマンドで生成します。

```bash
python3 ~/.codex/skills/run-explainer-page/scripts/render_fast.py \
  --input /absolute/path/to/input.json \
  --output /tmp/explainer-publish-scope/index.html \
  --open
```

Claude Code 側だけへ導入した場合は、パスを `~/.claude/skills/run-explainer-page/` に読み替えてください。

## 注意

FULL モードは、参照先の画像生成・探索スキルなどが環境にない場合、その機能を利用できません。人間向け確認依頼を高速に HTML 化する FAST モードは単体で動作します。
