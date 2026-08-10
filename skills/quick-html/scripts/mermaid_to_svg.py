#!/usr/bin/env python3
"""Convert a Mermaid flowchart to a local SVG that passes render_story's SVG safety validation.

Usage: mermaid_to_svg.py --input flow.mmd --output diagrams/flow.svg
Requires npx (@mermaid-js/mermaid-cli is fetched on demand). No CDN is used at viewing time.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


MERMAID_CLI = "@mermaid-js/mermaid-cli@11.16.0"
DEFAULT_CONFIG = {
    "securityLevel": "strict",
    "htmlLabels": False,
    "flowchart": {"htmlLabels": False},
    "theme": "neutral",
}


def _load_render_story():
    specification = importlib.util.spec_from_file_location("render_story", Path(__file__).resolve().parent / "render_story.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_render_story = _load_render_story()
ContractError = _render_story.ContractError


def postprocess(svg_path: Path) -> None:
    """Strip the unused xlink namespace declaration mermaid emits, then validate."""
    text = svg_path.read_text(encoding="utf-8")
    without_declaration = re.sub(r'\s*xmlns:xlink="[^"]*"', "", text)
    if "xlink:" not in without_declaration:
        svg_path.write_text(without_declaration, encoding="utf-8")
    _render_story._validate_svg(svg_path)


def convert(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle)
        config_path = Path(handle.name)
    try:
        result = subprocess.run(
            ["npx", "-y", MERMAID_CLI, "-i", str(input_path), "-o", str(output_path), "-c", str(config_path), "-b", "transparent"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode or not output_path.is_file():
            raise ContractError(f"mermaid-cli failed: {result.stderr.strip() or result.stdout.strip() or 'no output'}")
    finally:
        config_path.unlink(missing_ok=True)
    postprocess(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        convert(args.input, args.output)
    except (ContractError, OSError) as error:
        print(f"mermaid_to_svg: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
