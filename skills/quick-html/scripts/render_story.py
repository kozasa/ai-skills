#!/usr/bin/env python3
"""Render a normalized implementation story as a dependency-free HTML report."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse


ROOT_KEYS = {
    "slug", "title", "summary", "background", "request", "story",
    "decisions", "implementation", "visuals", "flow", "verification",
    "constraints", "references",
}
STORY_KEYS = {"title", "body", "evidence"}
DECISION_KEYS = {"title", "body", "reason"}
IMPLEMENTATION_KEYS = {"title", "body"}
VISUAL_KEYS = {"title", "type", "path", "description"}
FLOW_KEYS = {"condition", "result"}
VERIFICATION_KEYS = {"title", "status", "details"}
REFERENCE_KEYS = {"label", "url", "description"}
VISUAL_TYPES = {"actual", "reconstructed", "screenshot"}
VERIFICATION_STATUSES = {"passed", "failed", "warning", "unverified"}
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
    if not value:
        raise ContractError(f"{path} must not be empty")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ContractError(f"{path}[{index}] must be an object")
    return value


def _strings(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    for index, item in enumerate(value):
        _require_string(item, f"{path}[{index}]")
    return value


def _safe_relative_path(value: str, path: str) -> str:
    candidate = PurePosixPath(value)
    if (
        not value.strip()
        or candidate.is_absolute()
        or ".." in candidate.parts
        or urlparse(value).scheme
        or value.startswith(("/", "\\"))
    ):
        raise ContractError(f"{path} must be a safe relative path")
    return value


def _optional_url(value: Any, path: str) -> str | None:
    if value is None:
        return None
    url = _require_string(value, path)
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return url
    try:
        return _safe_relative_path(url, path)
    except ContractError as error:
        raise ContractError(f"{path} must be https, a safe relative path, or null") from error


def validate_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("payload must be an object")
    _reject_unknown(value, ROOT_KEYS, "payload")
    for field in ("slug", "title", "summary", "background", "request"):
        _require_string(value.get(field), field)
    if not SLUG.fullmatch(value["slug"]):
        raise ContractError("slug must be lowercase kebab-case")

    specs = (
        ("story", STORY_KEYS, ("title", "body", "evidence")),
        ("decisions", DECISION_KEYS, ("title", "body", "reason")),
        ("implementation", IMPLEMENTATION_KEYS, ("title", "body")),
        ("flow", FLOW_KEYS, ("condition", "result")),
        ("verification", VERIFICATION_KEYS, ("title", "status", "details")),
        ("references", REFERENCE_KEYS, ("label", "description")),
    )
    for field, keys, required in specs:
        for index, item in enumerate(_objects(value.get(field), field)):
            _reject_unknown(item, keys, f"{field}[{index}]")
            for name in required:
                _require_string(item.get(name), f"{field}[{index}].{name}")

    for index, item in enumerate(_objects(value.get("visuals"), "visuals")):
        _reject_unknown(item, VISUAL_KEYS, f"visuals[{index}]")
        for name in ("title", "type", "description"):
            _require_string(item.get(name), f"visuals[{index}].{name}")
        if item["type"] not in VISUAL_TYPES:
            raise ContractError(f"visuals[{index}].type must be actual, reconstructed, or screenshot")
        if "path" in item and item["path"] is not None:
            _safe_relative_path(_require_string(item["path"], f"visuals[{index}].path"), f"visuals[{index}].path")

    for index, item in enumerate(value["verification"]):
        if item["status"] not in VERIFICATION_STATUSES:
            raise ContractError(f"verification[{index}].status must be passed, failed, warning, or unverified")
    for index, item in enumerate(value["references"]):
        item["url"] = _optional_url(item.get("url"), f"references[{index}].url")
    _strings(value.get("constraints"), "constraints")
    return value


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _cards(items: list[dict[str, Any]], extra: str | None = None) -> str:
    cards = []
    for item in items:
        tail = f'<p class="reason"><strong>理由:</strong> {_escape(item[extra])}</p>' if extra else ""
        cards.append(f'<article class="card"><h3>{_escape(item["title"])}</h3><p>{_escape(item["body"])}</p>{tail}</article>')
    return "".join(cards)


def _story(items: list[dict[str, Any]]) -> str:
    return "".join(
        f'<li><span class="step">{index}</span><article class="card story-card"><h3>{_escape(item["title"])}</h3>'
        f'<p>{_escape(item["body"])}</p><p class="meta">根拠: {_escape(item["evidence"])}</p></article></li>'
        for index, item in enumerate(items, 1)
    )


def _visuals(items: list[dict[str, Any]]) -> str:
    labels = {"actual": "実装画面", "reconstructed": "説明用再構成", "screenshot": "スクリーンショット"}
    rendered = []
    for item in items:
        label = labels[item["type"]]
        path = item.get("path")
        if path and item["type"] in {"actual", "reconstructed"}:
            media = f'<iframe src="{_escape(path)}" title="{_escape(item["title"])}" sandbox="allow-scripts"></iframe>'
        elif path and item["type"] == "screenshot":
            media = f'<img src="{_escape(path)}" alt="{_escape(item["title"])}">'
        else:
            media = '<div class="visual-empty">プレビューはありません</div>'
        rendered.append(
            f'<figure><div class="visual-head"><span class="tag">{label}</span><strong>{_escape(item["title"])}</strong></div>'
            f'{media}<figcaption>{_escape(item["description"])}</figcaption></figure>'
        )
    return "".join(rendered)


def _flow(items: list[dict[str, Any]]) -> str:
    return "".join(
        f'<div class="flow-row"><span>{_escape(item["condition"])}</span><b aria-hidden="true">→</b><strong>{_escape(item["result"])}</strong></div>'
        for item in items
    )


def _verification(items: list[dict[str, Any]]) -> str:
    labels = {"passed": "PASS", "failed": "FAIL", "warning": "注意", "unverified": "未確認"}
    return "".join(
        f'<div class="check"><span class="status {item["status"]}">{labels[item["status"]]}</span>'
        f'<p><strong>{_escape(item["title"])}</strong><br>{_escape(item["details"])}</p></div>'
        for item in items
    )


def _references(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        label = _escape(item["label"])
        url = item.get("url")
        heading = f'<a href="{_escape(url)}">{label}</a>' if url else f'<span class="reference-label">{label}（参照不可）</span>'
        rows.append(f'<div class="reference">{heading}<p>{_escape(item["description"])}</p></div>')
    return "".join(rows)


def render(payload: dict[str, Any], template: str) -> str:
    replacements = {
        "{{TITLE}}": _escape(payload["title"]),
        "{{SUMMARY}}": _escape(payload["summary"]),
        "{{BACKGROUND}}": _escape(payload["background"]),
        "{{REQUEST}}": _escape(payload["request"]),
        "{{STORY}}": _story(payload["story"]),
        "{{DECISIONS}}": _cards(payload["decisions"], "reason"),
        "{{IMPLEMENTATION}}": _cards(payload["implementation"]),
        "{{VISUALS}}": _visuals(payload["visuals"]),
        "{{FLOW}}": _flow(payload["flow"]),
        "{{VERIFICATION}}": _verification(payload["verification"]),
        "{{CONSTRAINTS}}": "".join(f'<li>{_escape(item)}</li>' for item in payload["constraints"]),
        "{{REFERENCES}}": _references(payload["references"]),
    }
    marker_pattern = re.compile(r"{{[A-Z_]+}}")
    unknown = sorted(set(marker_pattern.findall(template)) - set(replacements))
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
        raise ContractError(result.stderr.strip() or f"exit {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        payload = validate_payload(json.loads(args.input.read_text(encoding="utf-8")))
        template = (Path(__file__).resolve().parents[1] / "templates/story.html").read_text(encoding="utf-8")
        page = render(payload, template)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
        temporary.write_text(page, encoding="utf-8")
        temporary.replace(args.output)
        if args.open:
            _open_file(args.output.resolve())
    except UnicodeDecodeError:
        print("render_story: input must be UTF-8", file=sys.stderr)
        return 2
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"render_story: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
