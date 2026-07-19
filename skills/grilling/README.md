# grilling

計画や設計を実行する前に、一問ずつ厳しく検証するスキルです。重要な曖昧さ、矛盾、依存関係、未確認の前提、リスクを解消し、最後に実行可能性を判定します。

## 主な動作

- 質問は一度に一つだけ
- 各質問にAIの推奨回答と理由を提示
- コードや資料から確認できる内容は、ユーザーに聞かず先に調査
- 確定事項、仮説、未決事項、却下案、矛盾、リスクを継続管理
- 重大な未決事項がなくなるまで固定上限なしで深掘り
- 終了時に三段階の実行可否判定と合意内容を提示

技術・プロダクト設計、事業計画、業務フロー、講座設計、AIエージェント設計などに利用できます。実装やファイル変更は自動では行いません。

## 起動例

```text
$grilling この計画を実行前に詰めてください
```

次のような依頼でも起動できます。

```text
この事業計画をgrillして
重要な穴がなくなるまで一問ずつ質問して
Stress-test this design before implementation
```

単に「計画を相談したい」と伝えただけでは、長いヒアリングを避けるため自動起動しません。

## Codexへの導入

```bash
git clone git@github.com:kozasa/ai-skills.git
test ! -e ~/.codex/skills/grilling
mkdir -p ~/.codex/skills
cp -R ai-skills/skills/grilling ~/.codex/skills/grilling
```

既存の `~/.codex/skills/grilling` を更新する場合は、内容を確認してから置き換えてください。

## Claude Codeへの導入

Codexと同じ実体を共有する場合:

```bash
test ! -e ~/.claude/skills/grilling
mkdir -p ~/.claude/skills
ln -s ~/.codex/skills/grilling ~/.claude/skills/grilling
```

Claude Codeだけで使う場合は、`skills/grilling` を `~/.claude/skills/grilling` にコピーしてください。

## ファイル構成

- `SKILL.md`: スキル本体
- `agents/openai.yaml`: Codex向けの表示情報と起動プロンプト
