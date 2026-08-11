from pathlib import Path
import unittest


SKILL = Path(__file__).parents[1] / "SKILL.md"
README = Path(__file__).parents[1] / "README.md"


class HumanHandoffContractTests(unittest.TestCase):
    def test_handoff_runs_for_merge_recommended_and_conditional_merge(self):
        text = SKILL.read_text()

        self.assertIn("マージ推奨または条件付きマージ", text)
        self.assertIn("human-handoff", text)
        self.assertIn("マージ非推奨では起動しない", text)
        self.assertIn("利用可能", text)
        self.assertIn("Codex / Claude Code 共通", text)

    def test_readme_documents_repository_independent_handoff(self):
        text = README.read_text()

        self.assertIn("すべてのリポジトリ", text)
        self.assertIn("マージ推奨", text)
        self.assertIn("条件付きマージ", text)
        self.assertIn("human-handoff", text)
        self.assertIn("Codex / Claude Code", text)


if __name__ == "__main__":
    unittest.main()
