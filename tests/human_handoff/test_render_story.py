import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/quick-html/scripts/render_story.py"
FIXTURE = Path(__file__).parent / "fixtures/implementation-story.json"


class StoryRendererTest(unittest.TestCase):
    def run_payload(self, payload):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name) / "input.json"
        output = Path(temp.name) / "index.html"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_story_renders_required_narrative_sections(self):
        result, output = self.run_payload(self.fixture())
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        for heading in ("背景", "依頼", "実装までのストーリー", "重要な判断", "実装されたもの", "実画面", "処理フロー", "検証結果", "参照"):
            self.assertIn(heading, page)
        self.assertLess(page.index("背景"), page.index("実装までのストーリー"))
        self.assertLess(page.index("実装までのストーリー"), page.index("実装されたもの"))

    def test_story_escapes_content_and_sandboxes_relative_preview(self):
        payload = self.fixture()
        payload["summary"] = '<script>alert("x")</script>'
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn('<script>alert("x")</script>', page)
        self.assertIn('src="previews/invoice.html"', page)
        self.assertIn('sandbox="allow-scripts"', page)

    def test_null_reference_is_plain_text_and_https_reference_is_clickable(self):
        result, output = self.run_payload(self.fixture())
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertIn('href="https://github.com/example/repo/pull/142"', page)
        self.assertIn("元の指示", page)
        self.assertNotIn('href="None"', page)

    def test_unsafe_preview_path_fails_closed(self):
        payload = self.fixture()
        payload["visuals"][0]["path"] = "../secret.html"
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("safe relative path", result.stderr)

    def test_unknown_root_key_fails_closed(self):
        payload = self.fixture()
        payload["unexpected"] = True
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown keys", result.stderr)

    def test_skill_docs_expose_story_triggers_and_repository_external_output(self):
        router = (ROOT / "skills/human-handoff/SKILL.md").read_text(encoding="utf-8")
        renderer = (ROOT / "skills/quick-html/SKILL.md").read_text(encoding="utf-8")
        for phrase in ("実装ストーリー", "PRの経緯", "review-loop"):
            self.assertIn(phrase, router)
        self.assertIn("scripts/render_story.py", renderer)
        self.assertIn("リポジトリ外", renderer)


if __name__ == "__main__":
    unittest.main()
