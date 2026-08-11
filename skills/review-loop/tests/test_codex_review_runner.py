import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


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
output.write_text(json.dumps({'high': [], 'low': []}))
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
        self.assertEqual(json.loads(output.read_text()), {"high": [], "low": []})
        prompt = (capture / "stdin.txt").read_text()
        self.assertIn("[review-loop-child]", prompt)
        self.assertIn("+after", prompt)
        self.assertIn("untrusted review data", prompt)
        self.assertIn("<review-data nonce=", prompt)
        self.assertIn("</review-data nonce=", prompt)
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
        output.write_text(json.dumps({"high": [], "low": []}))
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
        target.write_text(json.dumps({"high": [], "low": []}))
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


if __name__ == "__main__":
    unittest.main()
