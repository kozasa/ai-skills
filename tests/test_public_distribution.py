from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PublicDistributionTest(unittest.TestCase):
    def test_public_skill_packages_are_complete(self):
        required = (
            "skills/human-handoff/SKILL.md",
            "skills/human-handoff/README.md",
            "skills/quick-html/SKILL.md",
            "skills/quick-html/README.md",
            "skills/quick-html/scripts/render_fast.py",
            "skills/quick-html/scripts/render_story.py",
            "skills/quick-html/templates/fast.html",
            "skills/quick-html/templates/story.html",
        )

        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual([], missing)

    def test_root_readme_documents_supported_installation_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for expected in (
            "~/.codex/skills",
            "~/.claude/skills",
            "AGENTS.md",
            "CLAUDE.md",
            "human-handoff",
            "quick-html",
            "エージェントにセットアップを依頼する",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, readme)

    def test_root_readme_auto_trigger_rule_names_the_router_skill(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("人間の判断が必要な確認依頼", readme)
        self.assertIn("複雑な完了報告", readme)
        self.assertIn("`human-handoff` skill を使う", readme)


if __name__ == "__main__":
    unittest.main()
