# HTML communication skills publication design

## Conclusion

`ai-skills` を `human-facing-communication` と `run-explainer-page` の公開配布上の正本とし、利用者とエージェントのどちらでも再現できる導入手順を README に含める。

## Goal

Codex / Claude Code の利用者が、任意のリポジトリで人間向けの確認依頼や複雑な完了報告を高速なローカル HTML として表示できるようにする。

## Distribution model

- 公開正本: `kozasa/ai-skills` の `skills/<skill-name>/`
- 実行用配置先:
  - Codex: `~/.codex/skills/<skill-name>/`
  - Claude Code: `~/.claude/skills/<skill-name>/`
- 自動発火を安定させるため、利用するリポジトリの `AGENTS.md` / `CLAUDE.md` に共通指示を追加する。
- グローバル設定へ同じ指示を置けば、個別リポジトリへの記載を省略できる。ただしリポジトリ固有の指示が優先・追加され得ることを明記する。

## Documentation

ルート README は次を提供する。

1. スキル一覧と用途
2. Git clone とコピーによる手動セットアップ
3. `AGENTS.md` / `CLAUDE.md` に貼る自動発火スニペット
4. エージェントへそのまま渡せるセットアップ依頼文
5. 更新方法と簡単な動作確認

各スキル README は、用途、構成、導入、呼び出し例、制約を説明する。

## Compatibility and safety

- FAST モードは Python 標準ライブラリだけで動作する。
- HTML はローカル生成のみで、外部送信や外部アセット取得を行わない。
- `human-facing-communication` は判断を代行せず、人間向け情報の整理と提示だけを担う。
- `run-explainer-page` は FAST / FULL の既存契約を維持する。

## Verification

- 必須ファイルと README 内の導入指示を自動テストする。
- FAST renderer の既存テストを配布リポジトリ内で実行する。
- サンプル JSON から HTML を生成し、結論が冒頭と末尾に表示されることを確認する。
- Research 側の移植元と公開配布物が一致することを `diff -ru` で確認する。

## Conclusion

公開正本、実行用コピー、自動発火指示を分離することで、本人の別 PC と第三者の両方が同じ手順で導入できる形にする。
