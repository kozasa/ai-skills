#!/usr/bin/env python3
"""Render normalized agent context as a dependency-free one-page HTML file."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


ROOT_KEYS = {
    "type",
    "slug",
    "title",
    "summary",
    "recommendation",
    "items",
    "details",
    "sources",
}
ITEM_KEYS = {"title", "body", "status"}
DETAIL_KEYS = {"title", "body"}
SOURCE_KEYS = {"label", "url"}
STATUSES = {"recommended", "warning", "neutral"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class ContractError(ValueError):
    pass


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _reject_unknown(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{path} has unknown keys: {', '.join(unknown)}")


def _objects(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ContractError(f"{path}[{index}] must be an object")
    return value


def validate_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("payload must be an object")
    _reject_unknown(value, ROOT_KEYS, "payload")

    kind = _require_string(value.get("type"), "type")
    if kind not in {"decision", "completion"}:
        raise ContractError("type must be decision or completion")
    slug = _require_string(value.get("slug"), "slug")
    if not SLUG.fullmatch(slug):
        raise ContractError("slug must be lowercase kebab-case")
    _require_string(value.get("title"), "title")
    _require_string(value.get("summary"), "summary")
    if "recommendation" in value:
        _require_string(value["recommendation"], "recommendation")

    for index, item in enumerate(_objects(value.get("items", []), "items")):
        _reject_unknown(item, ITEM_KEYS, f"items[{index}]")
        _require_string(item.get("title"), f"items[{index}].title")
        _require_string(item.get("body"), f"items[{index}].body")
        status = item.get("status", "neutral")
        if not isinstance(status, str):
            raise ContractError(f"items[{index}].status must be a string")
        if status not in STATUSES:
            raise ContractError(
                f"items[{index}].status must be recommended, warning, or neutral"
            )

    for index, detail in enumerate(_objects(value.get("details", []), "details")):
        _reject_unknown(detail, DETAIL_KEYS, f"details[{index}]")
        _require_string(detail.get("title"), f"details[{index}].title")
        _require_string(detail.get("body"), f"details[{index}].body")

    for index, source in enumerate(_objects(value.get("sources", []), "sources")):
        _reject_unknown(source, SOURCE_KEYS, f"sources[{index}]")
        _require_string(source.get("label"), f"sources[{index}].label")
        _require_string(source.get("url"), f"sources[{index}].url")
    return value


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _render_items(payload: dict[str, Any]) -> str:
    items = payload.get("items", [])
    if not items:
        return '<p class="empty">追加項目はありません。</p>'
    rendered = []
    for item in items:
        status = item.get("status", "neutral")
        rendered.append(
            f'<article class="item {status}"><h3>{_escape(item["title"])}</h3>'
            f'<p>{_escape(item["body"])}</p></article>'
        )
    return "".join(rendered)


def _render_details(payload: dict[str, Any]) -> str:
    details = payload.get("details", [])
    if not details:
        return ""
    rows = "".join(
        f'<details><summary>{_escape(item["title"])}</summary>'
        f'<p>{_escape(item["body"])}</p></details>'
        for item in details
    )
    return (
        '<section aria-labelledby="details-title"><h2 id="details-title">詳細</h2>'
        f"{rows}</section>"
    )


def _render_sources(payload: dict[str, Any]) -> str:
    sources = payload.get("sources", [])
    if not sources:
        return ""
    rows = "".join(
        f'<li>{_escape(item["label"])} — <code>{_escape(item["url"])}</code></li>'
        for item in sources
    )
    return (
        '<section aria-labelledby="sources-title"><h2 id="sources-title">参照</h2>'
        f'<ul class="sources">{rows}</ul></section>'
    )


def render(payload: dict[str, Any], template: str) -> str:
    recommendation = payload.get("recommendation")
    recommendation_text = recommendation or "推奨案は未指定です。"
    conclusion = (
        '<div class="conclusion" data-conclusion="true"><h2>結論</h2>'
        f'<p>{_escape(recommendation_text)}</p></div>'
    )
    replacements = {
        "{{KICKER}}": "判断・確認" if payload["type"] == "decision" else "完了報告",
        "{{TITLE}}": _escape(payload["title"]),
        "{{SUMMARY}}": _escape(payload["summary"]),
        "{{ITEMS_TITLE}}": "確認事項" if payload["type"] == "decision" else "実施内容",
        "{{ITEMS}}": _render_items(payload),
        "{{DETAILS}}": _render_details(payload),
        "{{SOURCES}}": _render_sources(payload),
        "{{TOP_CONCLUSION}}": conclusion,
        "{{BOTTOM_CONCLUSION}}": conclusion,
    }
    marker_pattern = re.compile(r"{{[A-Z_]+}}")
    template_markers = set(marker_pattern.findall(template))
    unknown = sorted(template_markers - set(replacements))
    if unknown:
        raise ContractError(f"template has unresolved markers: {', '.join(unknown)}")
    return marker_pattern.sub(lambda match: replacements[match.group(0)], template)


def _open_file(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif sys.platform.startswith("linux"):
        command = ["xdg-open", str(path)]
    elif sys.platform == "win32":
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        raise ContractError(f"no opener configured for {sys.platform}")
    if shutil.which(command[0]) is None:
        raise ContractError(f"opener not found: {command[0]}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or f"exit {result.returncode}"
        raise ContractError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--open", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = validate_payload(json.loads(args.input.read_text(encoding="utf-8")))
        template_path = Path(__file__).resolve().parents[1] / "templates" / "fast.html"
        page = render(payload, template_path.read_text(encoding="utf-8"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
        temporary.write_text(page, encoding="utf-8")
        temporary.replace(args.output)
        if args.open:
            try:
                _open_file(args.output.resolve())
            except ContractError as error:
                print(f"HTML generated but open failed: {error}", file=sys.stderr)
                return 2
    except UnicodeDecodeError:
        print("render_fast: input must be UTF-8", file=sys.stderr)
        return 2
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"render_fast: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
