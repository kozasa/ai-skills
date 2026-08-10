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
                "output=$(printf '%s\\n' \"$prompt\" | sed -n 's/^FINAL_OUTPUT=//p')\n"
                "printf '\\211PNG\\r\\n\\032\\n' > \"$output\"\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            prompt = root / "prompt.txt"
            prompt.write_text("重要な変更を説明する抽象図。顧客情報や固有名詞は含めない。", encoding="utf-8")
            output = root / "handoff/images/overview.png"
            args_log = root / "args.txt"
            prompt_log = root / "stdin.txt"
            environment = os.environ.copy()
            environment.update(PATH=f"{fake_bin}:{environment['PATH']}", FAKE_ARGS=str(args_log), FAKE_PROMPT=str(prompt_log))

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
            forwarded = prompt_log.read_text(encoding="utf-8")
            self.assertIn("Use the installed imagegen skill and the built-in ImageGen tool", forwarded)
            self.assertIn("Japanese title, step labels, branch conditions, outcomes, and one takeaway", forwarded)
            self.assertIn("Do not replace requested Japanese labels with English", forwarded)
            self.assertIn(f"FINAL_OUTPUT={output.resolve()}", forwarded)


if __name__ == "__main__":
    unittest.main()
