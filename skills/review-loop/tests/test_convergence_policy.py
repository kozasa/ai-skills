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
