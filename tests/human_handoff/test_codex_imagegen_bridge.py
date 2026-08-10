import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "skills/human-handoff/scripts/generate-with-codex-imagegen.sh"


class CodexImagegenBridgeTest(unittest.TestCase):
    def test_invokes_ephemeral_codex_and_verifies_png_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_codex = fake_bin / "codex"
            fake_codex.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "printf '%s\\n' \"$@\" > \"$FAKE_ARGS\"\n"
                "prompt=$(cat)\n"
                "printf '%s' \"$prompt\" > \"$FAKE_PROMPT\"\n"
                "output=\"$CODEX_IMAGEGEN_OUTPUT_ROOT/generated.png\"\n"
                "printf '\\211\\120\\116\\107\\015\\012\\032\\012\\000\\000\\000\\015\\111\\110\\104\\122\\000\\000\\000\\020\\000\\000\\000\\011\\010\\006\\000\\000\\000\\073\\052\\254\\062\\000\\000\\000\\017\\111\\104\\101\\124\\170\\234\\143\\140\\030\\005\\243\\200\\012\\000\\000\\002\\111\\000\\001\\331\\137\\177\\235\\000\\000\\000\\000\\111\\105\\116\\104\\256\\102\\140\\202' > \"$output\"\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            prompt = root / "prompt.txt"
            prompt.write_text("重要な変更を説明する抽象図。顧客情報や固有名詞は含めない。", encoding="utf-8")
            output = root / "handoff/images/overview.png"
            args_log = root / "args.txt"
            prompt_log = root / "stdin.txt"
            generated_root = root / "generated"
            generated_root.mkdir()
            environment = os.environ.copy()
            environment.update(PATH=f"{fake_bin}:{environment['PATH']}", FAKE_ARGS=str(args_log), FAKE_PROMPT=str(prompt_log), CODEX_IMAGEGEN_OUTPUT_ROOT=str(generated_root))

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
            work_directory = Path(argument_lines[argument_lines.index("-C") + 1]).resolve()
            self.assertNotEqual(work_directory, output.parent.resolve())
            forwarded = prompt_log.read_text(encoding="utf-8")
            self.assertIn("Use the installed imagegen skill and the built-in ImageGen tool", forwarded)
            self.assertIn("Japanese title, step labels, branch conditions, outcomes, and one takeaway", forwarded)
            self.assertIn("Do not replace requested Japanese labels with English", forwarded)

    def test_replace_allows_a_verified_retry_to_the_same_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_codex = fake_bin / "codex"
            fake_codex.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "prompt=$(cat)\n"
                "output=\"$CODEX_IMAGEGEN_OUTPUT_ROOT/generated.png\"\n"
                "printf '\\211\\120\\116\\107\\015\\012\\032\\012\\000\\000\\000\\015\\111\\110\\104\\122\\000\\000\\000\\020\\000\\000\\000\\011\\010\\006\\000\\000\\000\\073\\052\\254\\062\\000\\000\\000\\017\\111\\104\\101\\124\\170\\234\\143\\140\\030\\005\\243\\200\\012\\000\\000\\002\\111\\000\\001\\331\\137\\177\\235\\000\\000\\000\\000\\111\\105\\116\\104\\256\\102\\140\\202' > \"$output\"\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            prompt = root / "prompt.txt"
            prompt.write_text("文字を読みやすく再生成する。", encoding="utf-8")
            output = root / "overview.png"
            output.write_bytes(b"old image")
            generated_root = root / "generated"
            generated_root.mkdir()
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            environment["CODEX_IMAGEGEN_OUTPUT_ROOT"] = str(generated_root)

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


if __name__ == "__main__":
    unittest.main()
