import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "skills/human-handoff/scripts/generate-with-codex-imagegen.sh"

FAKE_CODEX = (
    "#!/bin/sh\n"
    "set -eu\n"
    "printf '%s\\n' \"$@\" > \"${FAKE_ARGS:-/dev/null}\"\n"
    "prompt=$(cat)\n"
    "printf '%s' \"$prompt\" > \"${FAKE_PROMPT:-/dev/null}\"\n"
    "if [ -n \"${FAKE_THREAD_ID:-}\" ]; then\n"
    "  printf '{\"type\":\"thread.started\",\"thread_id\":\"%s\"}\\n' \"$FAKE_THREAD_ID\"\n"
    "  thread_dir=\"$CODEX_IMAGEGEN_OUTPUT_ROOT/$FAKE_THREAD_ID\"\n"
    "else\n"
    "  thread_dir=\"$CODEX_IMAGEGEN_OUTPUT_ROOT/no-thread\"\n"
    "fi\n"
    "printf '%s\\n' '{\"type\":\"turn.started\"}'\n"
    "mkdir -p \"$thread_dir\"\n"
    "cp \"$FAKE_PNG\" \"$thread_dir/exec-image.png\"\n"
    "waited=0\n"
    "while [ \"${FAKE_WAIT_FOR_PNGS:-0}\" -gt \"$(find \"$CODEX_IMAGEGEN_OUTPUT_ROOT\" -type f -name '*.png' | wc -l)\" ] && [ \"$waited\" -lt 100 ]; do\n"
    "  sleep 0.1\n"
    "  waited=$((waited + 1))\n"
    "done\n"
)


def png_bytes(width, height):
    def chunk(chunk_type, payload):
        return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * (width * 4) for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def png_size(data):
    return struct.unpack(">II", data[16:24])


class CodexImagegenBridgeTest(unittest.TestCase):
    def make_fixture(self, root):
        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text(FAKE_CODEX, encoding="utf-8")
        fake_codex.chmod(0o755)
        generated_root = root / "generated"
        generated_root.mkdir()
        small_png = root / "small.png"
        small_png.write_bytes(png_bytes(16, 9))
        large_png = root / "large.png"
        large_png.write_bytes(png_bytes(32, 18))
        environment = os.environ.copy()
        environment.update(
            PATH=f"{fake_bin}:{environment['PATH']}",
            CODEX_IMAGEGEN_OUTPUT_ROOT=str(generated_root),
            FAKE_PNG=str(small_png),
            FAKE_THREAD_ID="01a2035b-cd97-79c3-b47c-07ef1295331e",
        )
        return environment, generated_root, small_png, large_png

    def test_invokes_ephemeral_codex_and_verifies_png_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment, _, _, _ = self.make_fixture(root)
            prompt = root / "prompt.txt"
            prompt.write_text("重要な変更を説明する抽象図。顧客情報や固有名詞は含めない。", encoding="utf-8")
            output = root / "handoff/images/overview.png"
            args_log = root / "args.txt"
            prompt_log = root / "stdin.txt"
            environment.update(FAKE_ARGS=str(args_log), FAKE_PROMPT=str(prompt_log))

            result = subprocess.run(
                [str(BRIDGE), "--prompt-file", str(prompt), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            arguments = args_log.read_text(encoding="utf-8")
            self.assertIn("--ephemeral", arguments)
            self.assertIn("workspace-write", arguments)
            self.assertIn("shell_tool", arguments)
            self.assertIn("view_image", arguments)
            argument_lines = arguments.splitlines()
            self.assertIn("--json", argument_lines)
            work_directory = Path(argument_lines[argument_lines.index("-C") + 1]).resolve()
            self.assertNotEqual(work_directory, output.parent.resolve())
            forwarded = prompt_log.read_text(encoding="utf-8")
            self.assertIn("Use the installed imagegen skill and the built-in ImageGen tool", forwarded)
            self.assertIn("Japanese title, step labels, branch conditions, outcomes, and one takeaway", forwarded)
            self.assertIn("Do not replace requested Japanese labels with English", forwarded)

    def test_replace_allows_a_verified_retry_to_the_same_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment, _, _, _ = self.make_fixture(root)
            prompt = root / "prompt.txt"
            prompt.write_text("文字を読みやすく再生成する。", encoding="utf-8")
            output = root / "overview.png"
            output.write_bytes(b"old image")

            result = subprocess.run(
                [str(BRIDGE), "--prompt-file", str(prompt), "--output", str(output), "--replace"],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(output.read_bytes(), b"old image")
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_two_concurrent_runs_with_the_same_output_root_both_succeed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment, _, small_png, large_png = self.make_fixture(root)
            prompt = root / "prompt.txt"
            prompt.write_text("並べて動かす図。", encoding="utf-8")
            runs = [
                ("11111111-aaaa-bbbb-cccc-000000000001", small_png, root / "first/overview.png"),
                ("22222222-aaaa-bbbb-cccc-000000000002", large_png, root / "second/overview.png"),
            ]
            processes = []
            for thread_id, source_png, output in runs:
                run_environment = dict(environment, FAKE_THREAD_ID=thread_id, FAKE_PNG=str(source_png), FAKE_WAIT_FOR_PNGS="2")
                processes.append(
                    subprocess.Popen(
                        [str(BRIDGE), "--prompt-file", str(prompt), "--output", str(output)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=run_environment,
                    )
                )
            results = [(process, *process.communicate(timeout=60)) for process in processes]

            for process, _, stderr in results:
                self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(png_size(runs[0][2].read_bytes()), (16, 9))
            self.assertEqual(png_size(runs[1][2].read_bytes()), (32, 18))

    def test_fails_without_thread_started_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment, _, _, _ = self.make_fixture(root)
            environment["FAKE_THREAD_ID"] = ""
            prompt = root / "prompt.txt"
            prompt.write_text("会話 ID が出ない場合。", encoding="utf-8")
            output_dir = root / "out"
            output = output_dir / "overview.png"

            result = subprocess.run(
                [str(BRIDGE), "--prompt-file", str(prompt), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("continue with the HTML overview only.", result.stderr)
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_fails_when_thread_id_has_unexpected_characters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment, _, _, _ = self.make_fixture(root)
            environment["FAKE_THREAD_ID"] = "../escape"
            prompt = root / "prompt.txt"
            prompt.write_text("会話 ID の形が変な場合。", encoding="utf-8")
            output_dir = root / "out"
            output = output_dir / "overview.png"

            result = subprocess.run(
                [str(BRIDGE), "--prompt-file", str(prompt), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("continue with the HTML overview only.", result.stderr)
            self.assertEqual(list(output_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
