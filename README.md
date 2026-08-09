# ai-skills

kozasaが管理する、Codex / Claude Code向けの再利用可能なAIエージェントスキル集です。

このリポジトリを公開上の正本として、普段使っているスキルを別の PC や他の利用者へ再現可能な形で配布します。

## Skills

| Skill | 概要 |
|---|---|
| [grilling](skills/grilling/) | 計画や設計を一問ずつ厳しく検証し、実行可能な合意内容へ整理します。 |
| [review-loop](skills/review-loop/) | レビューと修正を反復し、人間向けの最終マージ判定を提示します。 |
| [human-facing-communication](skills/human-facing-communication/) | 確認依頼や複雑な完了報告を、人間が短時間で判断できる形式へ整理します。 |
| [run-explainer-page](skills/run-explainer-page/) | 入力文脈から1枚 HTML を生成します。確認依頼向けの高速な FAST モードを含みます。 |

詳しい使い方は、各スキルの README を参照してください。

## セットアップ

### 1. リポジトリを取得する

```bash
git clone https://github.com/kozasa/ai-skills.git
cd ai-skills
```

すでに clone 済みなら `git pull --ff-only` で更新します。

### 2. スキルを配置する

Codex:

```bash
mkdir -p ~/.codex/skills/human-facing-communication
mkdir -p ~/.codex/skills/run-explainer-page
cp -R skills/human-facing-communication/. ~/.codex/skills/human-facing-communication/
cp -R skills/run-explainer-page/. ~/.codex/skills/run-explainer-page/
```

Claude Code:

```bash
mkdir -p ~/.claude/skills/human-facing-communication
mkdir -p ~/.claude/skills/run-explainer-page
cp -R skills/human-facing-communication/. ~/.claude/skills/human-facing-communication/
cp -R skills/run-explainer-page/. ~/.claude/skills/run-explainer-page/
```

両方使う場合は、両方の配置先へコピーします。更新時も同じコピーコマンドを実行してください。

## 自動的に HTML を使わせる

スキルを配置すると明示的に呼び出せます。ただし、通常の会話中にエージェントが確認依頼や完了報告を自動判定する精度を上げるには、指示ファイルにも発火ルールを追加します。

- Codex: 対象リポジトリの `AGENTS.md`
- Claude Code: 対象リポジトリの `CLAUDE.md`

両方へ、次の同じ指示を追加してください。

```md
## Human-facing communication

人間の判断が必要な確認依頼がある場合、または複雑な完了報告を返す場合は、
`human-facing-communication` skill を使う。

短い事実、一行の進捗、文脈が明白な単純な質問は通常の文章で返してよい。
```

この設定により、単純な返答まで毎回 HTML になることを避けつつ、読む負担が大きい場面だけ FAST HTML を使えます。

### すべてのリポジトリで使う場合

自分の全リポジトリで同じ動作にしたい場合は、上記の指示をユーザー共通ファイルにも置けます。

- Codex: `~/.codex/AGENTS.md`
- Claude Code: `~/.claude/CLAUDE.md`

リポジトリ側の `AGENTS.md` / `CLAUDE.md` に同じ指示を書く方法は、そのリポジトリを他の PC や他の利用者が扱う場合にも設定を共有しやすい方法です。

## エージェントにセットアップを依頼する

Codex または Claude Code に、次の文章をそのまま渡せます。

```text
https://github.com/kozasa/ai-skills から
human-facing-communication と run-explainer-page をセットアップしてください。

要件:
- 既存のファイルや指示を消さずに作業する
- Codex では ~/.codex/skills、Claude Code では ~/.claude/skills へ配置する
- 私が両方を使っている場合は両方へ配置する
- 現在のリポジトリの AGENTS.md / CLAUDE.md が存在する場合は、README にある
  Human-facing communication の自動発火ルールを、重複しないよう追記する
- リポジトリ共通ではなく全リポジトリで使いたいと伝えた場合は、
  ~/.codex/AGENTS.md / ~/.claude/CLAUDE.md へ同じルールを追記する
- 最後に FAST モードでサンプル HTML を生成し、生成先を教える
```

エージェントには、既存の指示ファイルを上書きせず追記・統合するよう明記しています。

## 動作確認

FAST renderer のテスト:

```bash
python3 -m unittest discover -s tests/human_facing_communication -v
```

サンプル HTML の生成方法は [run-explainer-page の README](skills/run-explainer-page/README.md) を参照してください。
