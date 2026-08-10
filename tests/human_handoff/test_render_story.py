import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "skills/quick-html/scripts/render_story.py"
FIXTURE = ROOT / "tests/human_handoff/fixtures/implementation-story"


class StoryRendererTest(unittest.TestCase):
    def payload(self):
        return json.loads((FIXTURE / "report.json").read_text(encoding="utf-8"))

    def run_payload(self, payload=None, mutate_asset=None, *, open_report=False, env=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        source = root / "source"
        output = root / "output"
        shutil.copytree(FIXTURE, source)
        if payload is not None:
            (source / "report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        if mutate_asset:
            mutate_asset(source)
        command = [sys.executable, str(RENDERER), "--input", str(source / "report.json"), "--output", str(output / "index.html")]
        if open_report:
            command.append("--open")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return result, output

    def render_valid_story(self):
        result, output = self.run_payload()
        self.assertEqual(result.returncode, 0, result.stderr)
        return (output / "index.html").read_text(encoding="utf-8"), output

    def test_story_first_order_and_asset_staging(self):
        page, output = self.render_valid_story()
        labels = ["今回の結論", "なぜ実装したか", "何をしたか", "どんな実装をしたか", "判断概要", "背景と依頼", "実装までのストーリー", "重要な判断", "実装されたもの", "変更の価値", "視覚的な証拠", "処理フロー", "検証結果", "次のアクション", "参照"]
        positions = [page.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue((output / "previews/operation-demo.html").is_file())
        self.assertTrue((output / "diagrams/bulk-update.svg").is_file())
        self.assertIn('sandbox="allow-scripts"', page)
        self.assertIn('src="diagrams/bulk-update.svg"', page)

    def test_at_a_glance_renders_as_a_causal_flow(self):
        page, _ = self.render_valid_story()
        self.assertIn('class="conclusion-flow"', page)
        self.assertEqual(page.count('class="conclusion-arrow"'), 2)
        self.assertIn('class="conclusion-node conclusion-node-main"', page)

    def test_at_a_glance_requires_what_why_and_how(self):
        for key in ("what", "why", "how"):
            with self.subTest(key=key):
                payload = self.payload()
                del payload["at_a_glance"][key]
                result, _ = self.run_payload(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"at_a_glance.{key} is required", result.stderr)

    def test_recommendation_status_labels(self):
        expected = {
            "merge-recommended": "マージ推奨",
            "conditional": "条件付きでマージ可能",
            "do-not-merge": "マージ非推奨",
        }
        for status, label in expected.items():
            with self.subTest(status=status):
                payload = self.payload()
                payload["recommendation"]["status"] = status
                if status == "merge-recommended":
                    for check in payload["verification"]:
                        if check["blocking"]:
                            check["status"] = "passed"
                result, output = self.run_payload(payload)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(label, (output / "index.html").read_text(encoding="utf-8"))

    def test_merge_recommended_rejects_incomplete_blocking_check(self):
        payload = self.payload()
        payload["recommendation"]["status"] = "merge-recommended"
        payload["verification"][0].update(status="unverified", blocking=True)
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("merge-recommended requires all blocking verification to pass", result.stderr)

    def test_unknown_key_and_marker_input_fail_closed_or_escape(self):
        payload = self.payload()
        payload["unknown"] = "x"
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        escaped = self.payload()
        escaped["summary"] = "{{TITLE}} <script>alert(1)</script>"
        result, output = self.run_payload(escaped)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn("{{TITLE}} &lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_reconstructed_preview_rejects_external_or_parent_access(self):
        tokens = ["fetch('/x')", "fetch ('/x')", "new XMLHttpRequest()", "new WebSocket('wss://x')", "window.parent.location='x'", 'location.href="https:"+"//example.com"', 'window.open("https:"+"//example.com")', 'link.setAttribute("href", target)', 'document.createElement("iframe")', '<meta http-equiv="refresh" content="0; url=//example.com">', "https://example.com/x.js", '<form action = "/submit"></form>', '<img src="//example.com/x">', '<style>@import "//example.com/x.css"</style>', '<style>body{background:url(//example.com/x)}</style>']
        for token in tokens:
            with self.subTest(token=token):
                def mutate(source, value=token):
                    path = source / "previews/operation-demo.html"
                    path.write_text(path.read_text(encoding="utf-8") + f"<script>{value}</script>", encoding="utf-8")
                result, _ = self.run_payload(mutate_asset=mutate)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unsafe reconstructed preview", result.stderr)

    def test_svg_rejects_active_or_external_content(self):
        tokens = ["<script>alert(1)</script>", "<foreignObject></foreignObject>", 'href="https://example.com"', 'href = "javascript:alert(1)"', 'xlink:href = "data:x"', '<style>@import "//example.com/x.css"</style>', '<style>@import "ftp://example.com/x.css"</style>', '<style>rect{fill:url(//example.com/x)}</style>', '<style>rect{fill:url(ftp://example.com/x)}</style>', "<!ENTITY x 'y'>"]
        for token in tokens:
            with self.subTest(token=token):
                def mutate(source, value=token):
                    path = source / "diagrams/bulk-update.svg"
                    path.write_text(path.read_text(encoding="utf-8").replace("</svg>", value + "</svg>"), encoding="utf-8")
                result, _ = self.run_payload(mutate_asset=mutate)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unsafe SVG", result.stderr)

    def test_visual_asset_symlink_is_rejected(self):
        def mutate(source):
            path = source / "previews/operation-demo.html"
            target = source / "preview-target.html"
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.unlink()
            path.symlink_to(target)
        result, _ = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 2)
        self.assertIn("asset not found or unsafe", result.stderr)

    def test_static_explanation_is_accepted_without_an_asset(self):
        payload = self.payload()
        payload["visuals"] = [{"title": "構造説明", "type": "static-explanation", "description": "実画面も再構成も利用できない場合の説明。"}]
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn("静的説明", page)
        self.assertIn("構造説明", page)

    def test_actual_html_preview_rejects_external_access(self):
        payload = self.payload()
        payload["visuals"][0]["type"] = "actual"
        def mutate(source):
            path = source / "previews/operation-demo.html"
            path.write_text(path.read_text(encoding="utf-8") + "<script>fetch('/private')</script>", encoding="utf-8")
        result, _ = self.run_payload(payload, mutate_asset=mutate)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe HTML preview", result.stderr)

    def test_evidence_visual_requires_a_path(self):
        for visual_type in ("actual", "reconstructed", "screenshot"):
            with self.subTest(visual_type=visual_type):
                payload = self.payload()
                payload["visuals"] = [{"title": "証拠", "type": visual_type, "description": "pathなし"}]
                result, _ = self.run_payload(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn("requires path", result.stderr)

    def test_iframe_visual_requires_an_html_extension(self):
        payload = self.payload()
        payload["visuals"][0]["path"] = "previews/operation-demo.txt"
        def mutate(source):
            original = source / "previews/operation-demo.html"
            original.rename(source / "previews/operation-demo.txt")
        result, _ = self.run_payload(payload, mutate_asset=mutate)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must use an .html or .htm path", result.stderr)

    def test_staged_html_preview_has_strict_csp_for_unlisted_network_apis(self):
        def mutate(source):
            path = source / "previews/operation-demo.html"
            path.write_text(path.read_text(encoding="utf-8").replace("</script>", 'navigator.sendBeacon("https:" + "//example.com", "x");</script>'), encoding="utf-8")
        result, output = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = (output / "previews/operation-demo.html").read_text(encoding="utf-8")
        self.assertIn("default-src 'none'", staged)
        self.assertIn("connect-src 'none'", staged)
        self.assertIn("form-action 'none'", staged)

    def test_preview_stages_safe_relative_script_and_stylesheet(self):
        def mutate(source):
            preview = source / "previews/operation-demo.html"
            preview.write_text(
                preview.read_text(encoding="utf-8").replace(
                    "</head>",
                    '<link rel="stylesheet" href="assets/demo.css"></head>',
                ).replace("</body>", '<img src="assets/demo.png"><script src="assets/demo.js"></script></body>'),
                encoding="utf-8",
            )
            assets = source / "previews/assets"
            assets.mkdir()
            (assets / "demo.css").write_text("button { color: #123456; }", encoding="utf-8")
            (assets / "demo.js").write_text("document.body.dataset.ready = 'true';", encoding="utf-8")
            (assets / "demo.png").write_bytes(b"fake-png")

        result, output = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "previews/assets/demo.css").is_file())
        self.assertTrue((output / "previews/assets/demo.js").is_file())
        self.assertTrue((output / "previews/assets/demo.png").is_file())
        staged = (output / "previews/operation-demo.html").read_text(encoding="utf-8")
        self.assertIn("script-src 'self' 'unsafe-inline'", staged)
        self.assertIn("style-src 'self' 'unsafe-inline'", staged)

    def test_preview_stages_recursive_javascript_module_imports(self):
        def mutate(source):
            preview = source / "previews/operation-demo.html"
            preview.write_text(
                preview.read_text(encoding="utf-8").replace(
                    "</body>", '<script type="module" src="assets/main.js"></script></body>'
                ),
                encoding="utf-8",
            )
            assets = source / "previews/assets"
            assets.mkdir()
            (assets / "main.js").write_text('import {\n  ready\n} from "./helper.js";\ndocument.body.dataset.ready = ready;', encoding="utf-8")
            (assets / "helper.js").write_text('export { ready } from "./nested.js";', encoding="utf-8")
            (assets / "nested.js").write_text('export const ready = "true";', encoding="utf-8")

        result, output = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("main.js", "helper.js", "nested.js"):
            self.assertTrue((output / f"previews/assets/{name}").is_file())

    def test_preview_stages_local_navigation_and_css_images(self):
        def mutate(source):
            preview = source / "previews/operation-demo.html"
            preview.write_text(
                preview.read_text(encoding="utf-8").replace(
                    "</head>", '<style>.hero { background:url("assets/inline.png") }</style></head>'
                ).replace("</body>", '<a href="details.html">詳細</a></body>'),
                encoding="utf-8",
            )
            (source / "previews/details.html").write_text(
                '<!doctype html><html><head><link rel="stylesheet" href="assets/details.css"></head><body>details</body></html>',
                encoding="utf-8",
            )
            assets = source / "previews/assets"
            assets.mkdir()
            (assets / "inline.png").write_bytes(b"inline")
            (assets / "details.css").write_text('.detail { background:url("images/detail.png") }', encoding="utf-8")
            images = assets / "images"
            images.mkdir()
            (images / "detail.png").write_bytes(b"detail")

        result, output = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in ("previews/details.html", "previews/assets/inline.png", "previews/assets/details.css", "previews/assets/images/detail.png"):
            self.assertTrue((output / relative).is_file(), relative)
        details = (output / "previews/details.html").read_text(encoding="utf-8")
        self.assertIn('http-equiv="Content-Security-Policy"', details)

    def test_preview_rejects_unsafe_relative_dependency(self):
        def mutate(source):
            preview = source / "previews/operation-demo.html"
            preview.write_text(
                preview.read_text(encoding="utf-8").replace(
                    "</body>", '<script src="../outside.js"></script></body>'
                ),
                encoding="utf-8",
            )

        result, _ = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe preview dependency", result.stderr)

    def test_preview_rejects_encoded_external_anchor(self):
        def mutate(source):
            preview = source / "previews/operation-demo.html"
            preview.write_text(
                preview.read_text(encoding="utf-8").replace(
                    "</body>", '<a href="&#104;ttps://example.com">leave</a></body>'
                ),
                encoding="utf-8",
            )

        result, _ = self.run_payload(mutate_asset=mutate)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe preview dependency", result.stderr)

    def test_relative_reference_is_staged_with_the_report(self):
        payload = self.payload()
        payload["references"][0]["url"] = "references/design.md"

        def mutate(source):
            references = source / "references"
            references.mkdir()
            (references / "design.md").write_text("# Design", encoding="utf-8")

        result, output = self.run_payload(payload, mutate_asset=mutate)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((output / "references/design.md").read_text(encoding="utf-8"), "# Design")
        self.assertIn('href="references/design.md"', (output / "index.html").read_text(encoding="utf-8"))

    def test_missing_relative_reference_is_rejected(self):
        payload = self.payload()
        payload["references"][0]["url"] = "references/missing.md"
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("asset not found or unsafe", result.stderr)

    def test_in_place_render_does_not_overwrite_source_preview(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(FIXTURE, root / "story")
        story = root / "story"
        preview = story / "previews/operation-demo.html"
        original = preview.read_text(encoding="utf-8")
        command = ["python3", str(RENDERER), "--input", str(story / "report.json"), "--output", str(story / "index.html")]
        for _ in range(2):
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(preview.read_text(encoding="utf-8"), original)
        staged = (story / ".story-assets/previews/operation-demo.html").read_text(encoding="utf-8")
        self.assertEqual(staged.count('http-equiv="Content-Security-Policy"'), 1)
        self.assertIn('src=".story-assets/previews/operation-demo.html"', (story / "index.html").read_text(encoding="utf-8"))

    def test_open_failure_does_not_fail_successful_render(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fake_bin = Path(temporary.name)
        opener = fake_bin / ("open" if sys.platform == "darwin" else "xdg-open")
        opener.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        opener.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
        result, output = self.run_payload(open_report=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "index.html").is_file())
        self.assertIn("failed to open output", result.stderr)

    def test_missing_opener_does_not_fail_successful_render(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        env = os.environ.copy()
        env["PATH"] = temporary.name
        result, output = self.run_payload(open_report=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "index.html").is_file())
        self.assertIn("failed to open output", result.stderr)

    def test_flow_diagram_must_be_well_formed_svg(self):
        replacements = ["<svg>", "<root></root>"]
        for content in replacements:
            with self.subTest(content=content):
                def mutate(source, value=content):
                    (source / "diagrams/bulk-update.svg").write_text(value, encoding="utf-8")
                result, _ = self.run_payload(mutate_asset=mutate)
                self.assertEqual(result.returncode, 2)
                self.assertIn("must be well-formed SVG", result.stderr)

    def test_skill_routes_and_boundaries_are_documented(self):
        handoff = (ROOT / "skills/human-handoff/SKILL.md").read_text(encoding="utf-8")
        quick = (ROOT / "skills/quick-html/SKILL.md").read_text(encoding="utf-8")
        for text in ["Story First", "人間のログイン", "再構成HTML", "最終判断は人間"]:
            self.assertIn(text, handoff)
        self.assertIn("matching normalized contract", handoff)
        self.assertIn("FAST or STORY mode", handoff)
        for text in ["merge-recommended", "conditional", "do-not-merge", "コードから再構成した操作デモ", "ローカルSVG", "外部通信"]:
            self.assertIn(text, quick)


if __name__ == "__main__":
    unittest.main()
