import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/quick-html/scripts/render_fast.py"
FIXTURES = Path(__file__).parent / "fixtures"


class FastRendererTest(unittest.TestCase):
    def run_payload(self, payload):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source = Path(temp.name) / "input.json"
        output = Path(temp.name) / "index.html"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(source),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def run_renderer(self, fixture: str):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        output = Path(temp.name) / "index.html"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input",
                str(FIXTURES / fixture),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def test_decision_renders_without_remote_assets_or_raw_script(self):
        result, output = self.run_renderer("decision.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertIn("確認したいこと", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("http://", page)

    def test_completion_renders_required_sections(self):
        result, output = self.run_renderer("completion.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertEqual(page.count("結論"), 2)
        self.assertIn("検証", page)

    def test_unknown_key_fails_closed(self):
        payload = json.loads(
            (FIXTURES / "decision.json").read_text(encoding="utf-8")
        )
        payload["unexpected"] = "value"
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "bad.json"
            output = Path(temp) / "index.html"
            source.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(source),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown keys", result.stderr)

    def test_missing_recommendation_is_not_replaced_with_summary(self):
        payload = json.loads(
            (FIXTURES / "decision.json").read_text(encoding="utf-8")
        )
        summary = payload["summary"]
        del payload["recommendation"]
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertIn("推奨案は未指定です", page)
        self.assertEqual(page.count(summary), 1)

    def test_explicit_null_collection_fails_closed(self):
        for field in ("items", "details", "sources"):
            with self.subTest(field=field):
                payload = json.loads(
                    (FIXTURES / "decision.json").read_text(encoding="utf-8")
                )
                payload[field] = None
                result, _ = self.run_payload(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"{field} must be an array", result.stderr)

    def test_non_string_status_fails_without_traceback(self):
        payload = json.loads(
            (FIXTURES / "decision.json").read_text(encoding="utf-8")
        )
        payload["items"][0]["status"] = []
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("status must be a string", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "invalid.json"
            output = Path(temp) / "index.html"
            source.write_bytes(b"{\xff}")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(source),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("input must be UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_marker_like_user_text_is_not_reprocessed(self):
        payload = json.loads(
            (FIXTURES / "decision.json").read_text(encoding="utf-8")
        )
        payload["summary"] = "テンプレート記法 {{ITEMS}} と {{TITLE}} を説明します。"
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        self.assertIn("テンプレート記法 {{ITEMS}} と {{TITLE}} を説明します。", page)
        self.assertIn("公開範囲", page)

    def test_conclusion_is_identical_first_and_last(self):
        payload = json.loads(
            (FIXTURES / "decision.json").read_text(encoding="utf-8")
        )
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = output.read_text(encoding="utf-8")
        recommendation = payload["recommendation"]
        conclusion_marker = 'data-conclusion="true"'
        self.assertEqual(page.count(conclusion_marker), 2)
        self.assertEqual(page.count(f"<p>{recommendation}</p>"), 2)
        first_conclusion = page.index(conclusion_marker)
        first_section = page.index("<section")
        last_section = page.rindex("</section>")
        last_conclusion = page.rindex(conclusion_marker)
        self.assertLess(first_conclusion, first_section)
        self.assertGreater(last_conclusion, last_section)

    def test_skill_declares_fast_and_full_routes(self):
        skill = (ROOT / "skills/quick-html/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## FAST mode", skill)
        self.assertIn("## FULL mode", skill)
        self.assertIn("scripts/render_fast.py", skill)
        self.assertIn("Do not run Phase 1 or Phase 3", skill)

    def test_judgment_skill_has_required_triggers_and_boundaries(self):
        skill = (ROOT / "skills/human-handoff/SKILL.md").read_text(
            encoding="utf-8"
        )
        required = [
            "human decision",
            "completion report",
            "prose-only",
            "$quick-html",
            "Do not reply to child agents",
        ]
        for phrase in required:
            self.assertIn(phrase, skill)


if __name__ == "__main__":
    unittest.main()
