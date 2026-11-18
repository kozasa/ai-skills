import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


RUNNER = Path(__file__).parents[1] / "scripts" / "codex_review.py"


class CodexReviewRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._run("git", "init", "-b", "main", cwd=self.repo)
        self._run("git", "config", "user.email", "test@example.com", cwd=self.repo)
        self._run("git", "config", "user.name", "Test", cwd=self.repo)
        (self.repo / "sample.txt").write_text("before\n")
        self._run("git", "add", "sample.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "initial", cwd=self.repo)
        (self.repo / "sample.txt").write_text("after\n")

    def tearDown(self):
        self.tempdir.cleanup()

    def _run(self, *args, cwd=None, env=None):
        return subprocess.run(
            args,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def _fake_codex(self, writes_result=True):
        path = self.root / "fake-codex"
        result_write = """
output = Path(args[args.index('-o') + 1])
output.write_text(json.dumps({'blockers': [], 'follow_ups': [], 'suggestions': []}))
""" if writes_result else ""
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "capture = Path(os.environ['FAKE_CAPTURE_DIR'])\n"
            "(capture / 'args.json').write_text(json.dumps(args))\n"
            "(capture / 'cwd.txt').write_text(os.getcwd())\n"
            "(capture / 'stdin.txt').write_text(sys.stdin.read())\n"
            + result_write
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_starts_with_default_python3(self):
        """スキルが指定する既定のpython3で、ランナーを起動できる。"""
        result = subprocess.run(
            ["python3", str(RUNNER), "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())

    def test_passes_fixed_diff_to_isolated_fresh_codex(self):
        capture = self.root / "capture"
        capture.mkdir()
        output = self.root / "review.json"
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(output),
                "--codex-bin", str(self._fake_codex()),
                "--timeout", "10",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(output.read_text()),
            {"blockers": [], "follow_ups": [], "suggestions": []},
        )
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("[review-loop-child]", prompt)
        self.assertIn("+after", prompt)
        self.assertIn("untrusted review data", prompt)
        self.assertIn("<review-data nonce=", prompt)
        self.assertIn("</review-data nonce=", prompt)
        self.assertIn("blockers", prompt)
        self.assertIn("follow_ups", prompt)
        self.assertIn("suggestions", prompt)
        self.assertNotEqual(Path((capture / "cwd.txt").read_text()), self.repo)
        args = json.loads((capture / "args.json").read_text())
        for required in (
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--output-schema",
        ):
            self.assertIn(required, args)

    def test_round_two_can_limit_review_to_fixed_paths(self):
        """2回目以降は修正対象の差分だけをレビュー入力へ含められる。"""
        related = self.repo / "related.txt"
        related.write_text("before related\n")
        self._run("git", "add", "related.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "add related", cwd=self.repo)
        (self.repo / "sample.txt").write_text("fixed sample\n")
        related.write_text("unrelated change\n")
        capture = self.root / "capture-focused"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "2",
                "--output", str(self.root / "focused.json"),
                "--codex-bin", str(self._fake_codex()),
                "--focus-path", "sample.txt",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("fixed sample", prompt)
        self.assertNotIn("unrelated change", prompt)
        self.assertIn("focused review", prompt)

    def test_fails_closed_when_codex_writes_no_result(self):
        capture = self.root / "capture-missing"
        capture.mkdir()
        output = self.root / "missing.json"
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(output),
                "--codex-bin", str(self._fake_codex(writes_result=False)),
                "--timeout", "10",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-empty review result", result.stderr)

    def test_rejects_untracked_symlink(self):
        outside = self.root / "outside.txt"
        outside.write_text("must not enter review packet\n")
        (self.repo / "linked.txt").symlink_to(outside)
        capture = self.root / "capture-symlink"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "symlink.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("untracked symlink", result.stderr)
        self.assertFalse((capture / "stdin.txt").exists())

    def test_removes_stale_result_before_codex_runs(self):
        capture = self.root / "capture-stale"
        capture.mkdir()
        output = self.root / "stale.json"
        output.write_text(json.dumps({"blockers": [], "follow_ups": [], "suggestions": []}))
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(output),
                "--codex-bin", str(self._fake_codex(writes_result=False)),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-empty review result", result.stderr)
        self.assertFalse(output.exists())

    def test_rejects_output_symlink_without_deleting_target(self):
        capture = self.root / "capture-output-symlink"
        capture.mkdir()
        target = self.root / "must-survive.json"
        target.write_text(json.dumps({"blockers": [], "follow_ups": [], "suggestions": []}))
        output = self.root / "output-link.json"
        output.symlink_to(target)
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(output),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output path must not be a symlink", result.stderr)
        self.assertTrue(target.exists())
        self.assertTrue(output.is_symlink())
        self.assertFalse((capture / "stdin.txt").exists())

    def test_rejects_oversized_untracked_file_before_reading_it(self):
        oversized = self.repo / "oversized.txt"
        oversized.write_bytes(b"x" * 1_500_001)
        capture = self.root / "capture-oversized"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "oversized.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("review packet exceeds", result.stderr)
        self.assertFalse((capture / "stdin.txt").exists())

    def test_records_large_untracked_binary_as_metadata(self):
        """大容量バイナリは内容を展開せず、ファイルサイズだけをレビュー対象へ含める。"""
        binary = self.repo / "handoff.png"
        binary.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 5_000_000)
        capture = self.root / "capture-large-binary"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "large-binary.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("<binary file: 5000008 bytes>", prompt)

    def test_includes_untracked_file_with_newline_in_name(self):
        unusual = self.repo / "line\nbreak.txt"
        unusual.write_text("must be reviewed\n")
        capture = self.root / "capture-unusual-name"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "unusual-name.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("must be reviewed", prompt)

    def test_limits_sparse_large_diff_to_codex_input_ceiling(self):
        """大きい疎な差分でもCodexの入力上限を超えるpacketを渡さない。"""
        large = self.repo / "large.txt"
        lines = [f"{index:05d}-" + ("x" * 94) + "\n" for index in range(12000)]
        large.write_text("".join(lines))
        self._run("git", "add", "large.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "large baseline", cwd=self.repo)
        for index in range(0, len(lines), 100):
            lines[index] = f"{index:05d}-" + ("y" * 94) + "\n"
        large.write_text("".join(lines))
        capture = self.root / "capture-large"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "large.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        packet = (capture / "stdin.txt").read_bytes()
        self.assertLessEqual(len(packet), 1_000_000)
        self.assertIn(b"+00000-", packet)
        self.assertIn(b"+11900-", packet)

    def test_uses_codex_character_limit_for_utf8_diff(self):
        """UTF-8のbyte数ではなくCodexが示す文字数上限でpacketを判定する。"""
        unicode_file = self.repo / "unicode.txt"
        unicode_file.write_text("あ" * 350000 + "\n")
        self._run("git", "add", "unicode.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "unicode baseline", cwd=self.repo)
        unicode_file.write_text("い" * 350000 + "\n")
        capture = self.root / "capture-unicode"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "unicode.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        packet = (capture / "stdin.txt").read_text()
        self.assertLessEqual(len(packet), 1_000_000)
        self.assertGreater(len(packet.encode("utf-8")), 1_000_000)

    def test_reviews_branch_changes_without_reversing_new_base_commits(self):
        """分岐後のbase変更をbranchによる削除としてレビューpacketへ入れない。"""
        self._run("git", "checkout", "--", "sample.txt", cwd=self.repo)
        self._run("git", "checkout", "-b", "feature", cwd=self.repo)
        (self.repo / "feature.txt").write_text("feature-only\n")
        self._run("git", "add", "feature.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "feature change", cwd=self.repo)
        self._run("git", "checkout", "main", cwd=self.repo)
        (self.repo / "base-only.txt").write_text("must-not-be-reversed\n")
        self._run("git", "add", "base-only.txt", cwd=self.repo)
        self._run("git", "commit", "-m", "base advanced", cwd=self.repo)
        self._run("git", "checkout", "feature", cwd=self.repo)
        (self.repo / "sample.txt").write_text("uncommitted\n")
        capture = self.root / "capture-diverged"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "diverged.json"),
                "--codex-bin", str(self._fake_codex()),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        packet = (capture / "stdin.txt").read_text()
        self.assertIn("feature-only", packet)
        self.assertIn("uncommitted", packet)
        self.assertNotIn("must-not-be-reversed", packet)

    def test_references_only_verified_unchanged_copies_when_opted_in(self):
        """明示オプション時だけ、変更のないGit blobの完全コピーを参照化する。"""
        source = self.repo / "vendor.js"
        source.write_text("vendor baseline\n" * 75000)
        self._run("git", "add", "vendor.js", cwd=self.repo)
        self._run("git", "commit", "-m", "vendor baseline", cwd=self.repo)
        (self.repo / "preview.js").write_bytes(source.read_bytes())
        capture = self.root / "capture-copies"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)
        command = [sys.executable, str(RUNNER), "--repo", str(self.repo),
                   "--base", "main", "--round", "1", "--output", str(self.root / "copies.json"),
                   "--codex-bin", str(self._fake_codex())]
        default = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(default.returncode, 0)
        result = subprocess.run(command + ["--reference-unchanged-copies"], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("preview.js", prompt)
        self.assertIn("vendor.js", prompt)
        self.assertIn("sha256", prompt)
        self.assertNotIn("vendor baseline", prompt)
        self.assertIn("+after", prompt)
        source.write_text("small baseline\n")
        self._run("git", "add", "vendor.js", cwd=self.repo)
        self._run("git", "commit", "-m", "small baseline", cwd=self.repo)
        source.write_text("changed vendor\n")
        (self.repo / "preview.js").write_bytes(source.read_bytes())
        result = subprocess.run(command + ["--reference-unchanged-copies"], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('### Untracked: "preview.js"\n\nchanged vendor',
                      (capture / "stdin.txt").read_text())

    def test_does_not_reference_branch_added_sources(self):
        """ブランチで新規追加されたファイルのコピーは本文を省略しない。"""
        self._run("git", "checkout", "-b", "feature", cwd=self.repo)
        (self.repo / "new.js").write_text("new implementation\n")
        self._run("git", "add", "new.js", cwd=self.repo)
        self._run("git", "commit", "-m", "new implementation", cwd=self.repo)
        (self.repo / "copy.js").write_text("new implementation\n")
        capture = self.root / "capture-new-copies"
        capture.mkdir()
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)
        result = subprocess.run([sys.executable, str(RUNNER), "--repo", str(self.repo),
            "--base", "main", "--round", "1", "--output", str(self.root / "new-copies.json"),
            "--codex-bin", str(self._fake_codex()), "--reference-unchanged-copies"],
            env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('### Untracked: "copy.js"\n\nnew implementation',
                      (capture / "stdin.txt").read_text())


    def _run_runner(self, capture, codex_bin, *extra):
        """偽の codex でランナーを 1 回起動し、結果を返す。"""
        env = os.environ.copy()
        env["FAKE_CAPTURE_DIR"] = str(capture)
        return subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo", str(self.repo),
                "--base", "main",
                "--round", "1",
                "--output", str(self.root / "model.json"),
                "--codex-bin", str(codex_bin),
                "--timeout", "10",
                *extra,
            ],
            env=env,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _config_values(args):
        """Codex の起動引数から -c の値だけを抜き出す。"""
        return [args[index + 1] for index, arg in enumerate(args) if arg == "-c"]

    def test_pins_default_model_and_effort(self):
        """既定ではモデル gpt-6.2-sol・深さ high を -c で Codex に渡す。"""
        capture = self.root / "capture-default-model"
        capture.mkdir()

        result = self._run_runner(capture, self._fake_codex())

        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((capture / "args.json").read_text())
        self.assertEqual(
            self._config_values(args),
            ['model="gpt-6.2-sol"', 'model_reasoning_effort="high"'],
        )
        self.assertLess(args.index("--ignore-user-config"), args.index("-c"))
        self.assertLess(args.index("-c"), args.index("-"))

    def test_model_and_effort_can_be_overridden(self):
        """--model と --effort を渡すと、その値で Codex を起動する。"""
        capture = self.root / "capture-override-model"
        capture.mkdir()

        result = self._run_runner(capture, self._fake_codex(),
                                  "--model", "gpt-6.1-terra", "--effort", "medium")

        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((capture / "args.json").read_text())
        self.assertEqual(
            self._config_values(args),
            ['model="gpt-6.1-terra"', 'model_reasoning_effort="medium"'],
        )

    def test_rejects_invalid_model_or_effort_without_starting_codex(self):
        """TOML 文字列を壊す値は失敗にし、Codex を起動しない。"""
        for option, value in (
            ("--model", 'gpt"; evil="x'),
            ("--model", "gpt\nx"),
            ("--model", ""),
            ("--effort", 'high"'),
            ("--effort", "high low"),
        ):
            with self.subTest(option=option, value=value):
                capture = self.root / f"capture-invalid-{abs(hash((option, value)))}"
                capture.mkdir()

                result = self._run_runner(capture, self._fake_codex(), option, value)

                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid", result.stderr)
                self.assertFalse((capture / "args.json").exists())

    def test_default_timeout_is_600_seconds(self):
        """--timeout を省くと Codex を 600 秒まで待つ。"""
        spec = importlib.util.spec_from_file_location("codex_review_under_test", RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        argv = ["codex_review.py", "--repo", ".", "--base", "main",
                "--round", "1", "--output", "out.json"]

        with mock.patch.object(sys, "argv", argv):
            args = module.parse_args()

        self.assertEqual(args.timeout, 600)

    def test_suggests_upgrading_cli_when_model_is_not_supported(self):
        """Codex が not supported で失敗したら、CLI を上げる案内をエラー文に出す。"""
        capture = self.root / "capture-unsupported"
        capture.mkdir()
        fake = self.root / "fake-codex-unsupported"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "capture = Path(os.environ['FAKE_CAPTURE_DIR'])\n"
            "(capture / 'args.json').write_text(json.dumps(sys.argv[1:]))\n"
            "sys.stdin.read()\n"
            "print(\"Error: model is not supported\", file=sys.stderr)\n"
            "sys.exit(1)\n"
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

        result = self._run_runner(capture, fake)

        self.assertEqual(result.returncode, 1)
        self.assertIn("codex --version", result.stderr)
        self.assertIn("0.169.1", result.stderr)
        args = json.loads((capture / "args.json").read_text())
        self.assertEqual(len(self._config_values(args)), 2)

    def test_plain_codex_failure_has_no_upgrade_hint(self):
        """not supported 以外の失敗では、CLI を上げる案内を出さない。"""
        capture = self.root / "capture-plain-failure"
        capture.mkdir()
        fake = self.root / "fake-codex-failure"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "sys.stdin.read()\n"
            "print(\"Error: network down\", file=sys.stderr)\n"
            "sys.exit(2)\n"
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

        result = self._run_runner(capture, fake)

        self.assertEqual(result.returncode, 1)
        self.assertIn("exited with status 2", result.stderr)
        self.assertNotIn("codex --version", result.stderr)


if __name__ == "__main__":
    unittest.main()
