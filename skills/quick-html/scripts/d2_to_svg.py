#!/usr/bin/env python3
"""Convert a D2 flow diagram to a local SVG that passes render_story's SVG safety validation.

Usage: d2_to_svg.py --input flow.d2 --output diagrams/flow.svg
Requires the d2 CLI (`brew install d2`). Renders in sketch mode; the embedded data: fonts
are self-contained, so no CDN or network access happens at viewing time.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys


D2_BINARY = "d2"
D2_ARGS = ["--sketch", "--theme", "0", "--pad", "20"]


def _load_render_story():
    specification = importlib.util.spec_from_file_location("render_story", Path(__file__).resolve().parent / "render_story.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_render_story = _load_render_story()
ContractError = _render_story.ContractError


def postprocess(svg_path: Path) -> None:
    """Strip the unused xlink namespace declaration, then validate."""
    text = svg_path.read_text(encoding="utf-8")
    without_declaration = re.sub(r'\s*xmlns:xlink="[^"]*"', "", text)
    if "xlink:" not in without_declaration:
        svg_path.write_text(without_declaration, encoding="utf-8")
    _render_story._validate_svg(svg_path)


def convert(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [D2_BINARY, *D2_ARGS, str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ContractError(f"d2 CLI not available (brew install d2): {error}") from error
    if result.returncode or not output_path.is_file():
        raise ContractError(f"d2 failed: {result.stderr.strip() or result.stdout.strip() or 'no output'}")
    postprocess(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        convert(args.input, args.output)
    except (ContractError, OSError) as error:
        print(f"d2_to_svg: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
