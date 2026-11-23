from pathlib import Path
import unittest


SKILL = Path(__file__).parents[1] / "SKILL.md"


class ConvergencePolicyTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text()

    def test_round_two_and_later_use_focused_review(self):
        """初回は全体、修正後は修正差分と影響範囲を確認する。"""
        self.assertIn("R1は変更全体", self.text)
        self.assertIn("R2以降は修正差分と影響範囲", self.text)
        self.assertIn("--focus-path", self.text)

    def test_claude_code_passes_focus_paths_to_code_review(self):
        """Claude Code では R1 は対象なし、R2以降は記録した対象パスを code-review に渡す。"""
        self.assertIn("R1は対象なしで起動する", self.text)
        self.assertIn("記録した対象パス（準備の手順4の欄）を `code-review` の対象として並べて渡す", self.text)
        self.assertIn("/code-review medium <path1> <path2>", self.text)
        self.assertIn("CHANGELOG.md#21329", self.text)

    def test_claude_code_r1_checks_upstream_before_no_target(self):
        """upstream が基準ブランチでなければ、R1 も親が固定した差分を渡す。"""
        self.assertIn("git rev-parse --abbrev-ref @{upstream}", self.text)
        self.assertIn("Phase 0）の引用", self.text)

    def test_claude_code_r1_requires_default_branch_and_explicit_base(self):
        """既定ブランチも基準ブランチと一致するときだけ対象なし。違えば親が差分ファイルで比べる相手を固定する。"""
        self.assertIn("git rev-parse --abbrev-ref origin/HEAD", self.text)
        self.assertIn("両方が基準ブランチ（`origin/main` 等）と一致するときだけ", self.text)
        self.assertIn("比べる相手を `code-review` に任せず親の側で固定する", self.text)
        self.assertIn("git diff <基準ブランチ>...HEAD", self.text)
        self.assertIn("その差分ファイルを対象として渡す", self.text)

    def test_findings_have_three_actionable_levels(self):
        """指摘分類ごとの処置が明記されている。"""
        self.assertIn("ブロッカー", self.text)
        self.assertIn("フォローアップ", self.text)
        self.assertIn("提案", self.text)
        self.assertNotIn("**high**", self.text)
        self.assertNotIn("**low**", self.text)

    def test_follow_ups_become_beads_and_conditional_merge(self):
        """ブロッカーがなく自動確認成功なら残課題を追跡して条件付き終了できる。"""
        self.assertIn("フォローアップごとに Beads", self.text)
        self.assertIn("フォローアップだけが残る", self.text)
        self.assertIn("条件付きマージ", self.text)


if __name__ == "__main__":
    unittest.main()
