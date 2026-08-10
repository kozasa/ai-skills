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
        labels = ["変更の要点と確認事項", "視覚的な証拠", "処理フロー", "判断概要", "人間が見る点", "未確認事項", "重要な判断", "実装されたもの", "検証結果", "次のアクション", "参照"]
        positions = [page.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('<a class="pr-link" href="https://github.com/example/shop-admin/pull/123">PRを開く', page)
        self.assertLess(page.index('class="pr-link"'), page.index("変更の要点と確認事項"))
        self.assertNotIn("やったこと → なぜ必要か → どう対応したか → 確認してほしいこと", page)
        self.assertNotIn("実装までのストーリー", page)
        self.assertNotIn("変更の価値", page)
        self.assertNotIn("背景と依頼", page)
        self.assertNotIn("ビフォーアフター", page)
        self.assertNotIn("実装プロセス", page)
        self.assertIn('class="overview-primary"', page)
        self.assertIn('class="overview-details"', page)
        self.assertIn('class="human-checks"', page)
        self.assertIn('実装されたもの</h2><div class="grid-one">', page)
        self.assertIn('差し戻してください。</p><div class="grid-one">', page)
        self.assertIn('次のアクション</h2><div class="grid-one">', page)
        self.assertIn('.overview-details{display:grid;grid-template-columns:1fr;', page)
        self.assertIn("beforeprint", page)
        self.assertIn("afterprint", page)
        self.assertNotIn("Implementation Story</span>", page)
        for value in self.payload()["at_a_glance"].values():
            self.assertIn(value, page)
        self.assertTrue((output / "previews/operation-demo.html").is_file())
        self.assertTrue((output / "diagrams/bulk-update.svg").is_file())
        self.assertIn('sandbox="allow-scripts"', page)
        self.assertIn('src="diagrams/bulk-update.svg"', page)
        self.assertIn('<details class="flow-steps"><summary>テキスト版フロー</summary>', page)
        self.assertIn('<div class="diagram-viewer">', page)
        self.assertIn('data-zoom="in"', page)
        self.assertIn('data-zoom="out"', page)
        self.assertIn('data-zoom="reset"', page)

    def test_implementation_is_sorted_by_importance_with_labels(self):
        payload = self.payload()
        payload["implementation"] = [
            {"title": "補助ログ", "body": "低優先の変更。", "importance": "low"},
            {"title": "画面文言", "body": "中優先の変更。", "importance": "medium"},
            {"title": "一括設定処理", "body": "中心の変更。", "importance": "high"},
        ]
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        positions = [page.index(title) for title in ("一括設定処理", "画面文言", "補助ログ")]
        self.assertEqual(positions, sorted(positions))
        for label in ("重要度: 大", "重要度: 中", "重要度: 小"):
            self.assertIn(label, page)

    def test_implementation_importance_is_required_and_validated(self):
        payload = self.payload()
        payload["implementation"][0].pop("importance")
        result, _ = self.run_payload(payload)
        self.assertEqual(result.returncode, 2)
        invalid = self.payload()
        invalid["implementation"][0]["importance"] = "critical"
        result, _ = self.run_payload(invalid)
        self.assertEqual(result.returncode, 2)
        self.assertIn("importance", result.stderr)

    def test_flow_steps_stay_visible_without_a_diagram(self):
        payload = self.payload()
        payload["flow"].pop("diagram_path")
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('<details class="flow-steps">', page)
        self.assertNotIn('<div class="diagram-viewer">', page)
        self.assertIn('class="flow"', page)

    def test_removed_sections_are_rejected_as_unknown_keys(self):
        for key, value in (("background", "旧背景"), ("request", "旧依頼"), ("impact", [{"title": "旧", "before": "b", "after": "a"}]), ("story", [{"title": "旧", "body": "b", "evidence": "e"}])):
            with self.subTest(key=key):
                payload = self.payload()
                payload[key] = value
                result, _ = self.run_payload(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unknown keys", result.stderr)

    def test_optional_imagegen_hero_is_staged_below_overview(self):
        payload = self.payload()
        payload["hero_visual"] = {
            "path": "images/handoff-overview.png",
            "alt": "変更全体を説明する生成イラスト",
            "caption": "重要なhandoff向けにimagegenで生成した補助図解。",
        }

        def add_image(source):
            image = source / "images/handoff-overview.png"
            image.parent.mkdir()
            image.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000100000000908060000003b2aac320000000f49444154789c63601805a3800a000002490001d95f7f9d0000000049454e44ae426082"))

        result, output = self.run_payload(payload, mutate_asset=add_image)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertTrue((output / "images/handoff-overview.png").is_file())
        self.assertLess(page.index("重要ポイントの説明図"), page.index("変更の要点と確認事項"))
        self.assertLess(page.index("変更の要点と確認事項"), page.index("判断概要"))
        self.assertIn('src="images/handoff-overview.png"', page)
        self.assertIn("重要なhandoff向けにimagegenで生成した補助図解。", page)

    def test_imagegen_hero_rejects_a_corrupt_png(self):
        payload = self.payload()
        payload["hero_visual"] = {"path": "images/handoff-overview.png", "alt": "概要", "caption": "説明"}

        def corrupt_image(source):
            image = source / "images/handoff-overview.png"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"fake-png")

        result, _ = self.run_payload(payload, mutate_asset=corrupt_image)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid PNG image", result.stderr)

    def test_imagegen_hero_rejects_a_non_widescreen_png(self):
        payload = self.payload()
        payload["hero_visual"] = {"path": "images/handoff-overview.png", "alt": "概要", "caption": "説明"}

        def square_image(source):
            image = source / "images/handoff-overview.png"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c6360000200000500017a5eab3f0000000049454e44ae426082"))

        result, _ = self.run_payload(payload, mutate_asset=square_image)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("16:9 PNG image", result.stderr)

    def test_imagegen_hero_rejects_indexed_png_without_palette(self):
        payload = self.payload()
        payload["hero_visual"] = {"path": "images/handoff-overview.png", "alt": "概要", "caption": "説明"}

        def missing_palette(source):
            image = source / "images/handoff-overview.png"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000100000000908030000000cf45c000000000c49444154789c636018a4000000990001443b224b0000000049454e44ae426082"))

        result, _ = self.run_payload(payload, mutate_asset=missing_palette)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid PNG image", result.stderr)

    def test_pr_url_is_optional_and_must_be_https(self):
        payload = self.payload()
        payload.pop("pr_url")
        result, output = self.run_payload(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (output / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="pr-link"', page)
        self.assertNotIn("{{", page)
        for invalid in ("http://github.com/example/shop-admin/pull/123", "github.com/example/pull/1", "previews/operation-demo.html"):
            with self.subTest(invalid=invalid):
                payload = self.payload()
                payload["pr_url"] = invalid
                result, _ = self.run_payload(payload)
                self.assertEqual(result.returncode, 2)
                self.assertIn("pr_url must be an https URL", result.stderr)

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

    def test_svg_allows_self_contained_data_fonts_but_not_data_imports(self):
        def add_font(source):
            path = source / "diagrams/bulk-update.svg"
            path.write_text(path.read_text(encoding="utf-8").replace("</svg>", '<style>@font-face{font-family:"d2";src:url("data:application/font-woff2;base64,AAAA")}</style></svg>'), encoding="utf-8")
        result, _ = self.run_payload(mutate_asset=add_font)
        self.assertEqual(result.returncode, 0, result.stderr)
        def add_import(source):
            path = source / "diagrams/bulk-update.svg"
            path.write_text(path.read_text(encoding="utf-8").replace("</svg>", '<style>@import url("data:text/css;base64,AAAA")</style></svg>'), encoding="utf-8")
        result, _ = self.run_payload(mutate_asset=add_import)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe SVG", result.stderr)
        for value in ('url("data:image/png;base64,AAAA")', 'url("data:text/html;base64,AAAA")'):
            with self.subTest(value=value):
                def add_non_font(source, css=value):
                    path = source / "diagrams/bulk-update.svg"
                    path.write_text(path.read_text(encoding="utf-8").replace("</svg>", f"<style>rect{{fill:{css}}}</style></svg>"), encoding="utf-8")
                result, _ = self.run_payload(mutate_asset=add_non_font)
                self.assertEqual(result.returncode, 2)
                self.assertIn("unsafe SVG", result.stderr)

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
        for text in ["merge-recommended", "conditional", "do-not-merge", "コードから再構成した操作デモ", "ローカルSVG", "外部通信", "PRを開く", "Mermaid"]:
            self.assertIn(text, quick)


if __name__ == "__main__":
    unittest.main()
