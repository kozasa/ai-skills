#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


ROOT_KEYS = {"slug", "title", "summary", "at_a_glance", "hero_visual", "pr_url", "recommendation", "decisions", "implementation", "visuals", "flow", "verification", "constraints", "next_actions", "references"}
OBJECT_SPECS = {
    "decisions": ({"title", "body", "reason"}, ("title", "body", "reason")),
    "implementation": ({"title", "body", "importance"}, ("title", "body", "importance")),
    "next_actions": ({"title", "body", "owner", "timing"}, ("title", "body", "owner", "timing")),
    "references": ({"label", "url", "description"}, ("label", "description")),
}
RECOMMENDATION_KEYS = {"status", "reason", "unverified", "human_checks"}
AT_A_GLANCE_KEYS = {"what", "why", "how", "human_decision"}
HERO_VISUAL_KEYS = {"path", "alt", "caption"}
VISUAL_KEYS = {"title", "type", "path", "description"}
FLOW_KEYS = {"title", "diagram_path", "description", "steps"}
FLOW_STEP_KEYS = {"condition", "result"}
VERIFICATION_KEYS = {"title", "status", "details", "blocking"}
RECOMMENDATION_STATUSES = {"merge-recommended", "conditional", "do-not-merge"}
VISUAL_TYPES = {"actual", "reconstructed", "screenshot", "static-explanation"}
VERIFICATION_STATUSES = {"passed", "failed", "warning", "unverified"}
IMPORTANCE_LEVELS = ("high", "medium", "low")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class ContractError(ValueError):
    pass


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path} must be an object")
    return value


def _list(value: Any, path: str, *, nonempty: bool = True) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ContractError(f"{path} must be a non-empty array")
    return value


def _keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{path} has unknown keys: {', '.join(unknown)}")


def _strings(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    items = _list(value, path, nonempty=nonempty)
    for index, item in enumerate(items):
        _string(item, f"{path}[{index}]")
    return items


def _relative(value: Any, path: str) -> str:
    text = _string(value, path)
    candidate = PurePosixPath(text)
    if "\\" in text or "%" in text or candidate.is_absolute() or ".." in candidate.parts or urlparse(text).scheme or any(ord(character) < 32 for character in text):
        raise ContractError(f"{path} must be a safe relative path")
    return text


def _url(value: Any, path: str) -> str | None:
    if value is None:
        return None
    text = _string(value, path)
    parsed = urlparse(text)
    if parsed.scheme == "https" and parsed.netloc:
        return text
    return _relative(text, path)


def validate_payload(value: object) -> dict[str, Any]:
    payload = _dict(value, "payload")
    _keys(payload, ROOT_KEYS, "payload")
    for field in ("slug", "title", "summary"):
        _string(payload.get(field), field)
    if not SLUG.fullmatch(payload["slug"]):
        raise ContractError("slug must be lowercase kebab-case")

    pr_url = payload.get("pr_url")
    if pr_url is not None:
        parsed = urlparse(_string(pr_url, "pr_url"))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ContractError("pr_url must be an https URL")

    at_a_glance = _dict(payload.get("at_a_glance"), "at_a_glance")
    _keys(at_a_glance, AT_A_GLANCE_KEYS, "at_a_glance")
    for field in AT_A_GLANCE_KEYS:
        _string(at_a_glance.get(field), f"at_a_glance.{field}")

    hero_visual = payload.get("hero_visual")
    if hero_visual is not None:
        hero_visual = _dict(hero_visual, "hero_visual")
        _keys(hero_visual, HERO_VISUAL_KEYS, "hero_visual")
        for field in HERO_VISUAL_KEYS:
            _string(hero_visual.get(field), f"hero_visual.{field}")
        hero_path = _relative(hero_visual["path"], "hero_visual.path")
        if PurePosixPath(hero_path).suffix.lower() != ".png":
            raise ContractError("hero_visual.path must use a PNG image")

    recommendation = _dict(payload.get("recommendation"), "recommendation")
    _keys(recommendation, RECOMMENDATION_KEYS, "recommendation")
    for field in ("status", "reason"):
        _string(recommendation.get(field), f"recommendation.{field}")
    if recommendation["status"] not in RECOMMENDATION_STATUSES:
        raise ContractError("recommendation.status must be merge-recommended, conditional, or do-not-merge")
    _strings(recommendation.get("unverified"), "recommendation.unverified")
    _strings(recommendation.get("human_checks"), "recommendation.human_checks", nonempty=True)

    for field, (allowed, required) in OBJECT_SPECS.items():
        for index, item in enumerate(_list(payload.get(field), field, nonempty=field != "decisions")):
            item = _dict(item, f"{field}[{index}]")
            _keys(item, allowed, f"{field}[{index}]")
            for name in required:
                _string(item.get(name), f"{field}[{index}].{name}")
            if field == "references":
                item["url"] = _url(item.get("url"), f"references[{index}].url")
            if field == "implementation" and item["importance"] not in IMPORTANCE_LEVELS:
                raise ContractError(f"implementation[{index}].importance must be high, medium, or low")

    for index, item in enumerate(_list(payload.get("visuals"), "visuals")):
        item = _dict(item, f"visuals[{index}]")
        _keys(item, VISUAL_KEYS, f"visuals[{index}]")
        for name in ("title", "type", "description"):
            _string(item.get(name), f"visuals[{index}].{name}")
        if item["type"] not in VISUAL_TYPES:
            raise ContractError(f"visuals[{index}].type must be actual, reconstructed, screenshot, or static-explanation")
        visual_path = item.get("path")
        if item["type"] != "static-explanation" and visual_path is None:
            raise ContractError(f"visuals[{index}].type {item['type']} requires path")
        if visual_path is not None:
            visual_path = _relative(visual_path, f"visuals[{index}].path")
        if item["type"] in {"actual", "reconstructed"} and PurePosixPath(visual_path).suffix.lower() not in {".html", ".htm"}:
            raise ContractError(f"visuals[{index}].type {item['type']} must use an .html or .htm path")

    flow = _dict(payload.get("flow"), "flow")
    _keys(flow, FLOW_KEYS, "flow")
    for field in ("title", "description"):
        _string(flow.get(field), f"flow.{field}")
    if flow.get("diagram_path") is not None:
        _relative(flow["diagram_path"], "flow.diagram_path")
    for index, step in enumerate(_list(flow.get("steps"), "flow.steps")):
        step = _dict(step, f"flow.steps[{index}]")
        _keys(step, FLOW_STEP_KEYS, f"flow.steps[{index}]")
        for field in FLOW_STEP_KEYS:
            _string(step.get(field), f"flow.steps[{index}].{field}")

    verification = _list(payload.get("verification"), "verification")
    for index, item in enumerate(verification):
        item = _dict(item, f"verification[{index}]")
        _keys(item, VERIFICATION_KEYS, f"verification[{index}]")
        for field in ("title", "status", "details"):
            _string(item.get(field), f"verification[{index}].{field}")
        if item["status"] not in VERIFICATION_STATUSES:
            raise ContractError(f"verification[{index}].status must be passed, failed, warning, or unverified")
        if not isinstance(item.get("blocking"), bool):
            raise ContractError(f"verification[{index}].blocking must be a boolean")
    if recommendation["status"] == "merge-recommended" and any(item["blocking"] and item["status"] != "passed" for item in verification):
        raise ContractError("merge-recommended requires all blocking verification to pass")
    _strings(payload.get("constraints"), "constraints", nonempty=True)
    return payload


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _cards(items, reason=None):
    return "".join(f'<article class="card"><h3>{_escape(item["title"])}</h3><p>{_escape(item["body"])}</p>' + (f'<p class="reason"><strong>理由:</strong> {_escape(item[reason])}</p>' if reason else "") + "</article>" for item in items)


def _recommendation(item):
    labels = {"merge-recommended": "マージ推奨", "conditional": "条件付きでマージ可能", "do-not-merge": "マージ非推奨"}
    unverified = "".join(f"<li>{_escape(value)}</li>" for value in item["unverified"]) or "<li>なし</li>"
    checks = "".join(f"<li>{_escape(value)}</li>" for value in item["human_checks"])
    return f'<section class="judgment"><span class="status {item["status"]}">{labels[item["status"]]}</span><h2>判断概要</h2><p>{_escape(item["reason"])}</p><div class="split"><div class="human-checks"><h3>人間が見る点</h3><ul>{checks}</ul></div><div><h3>未確認事項</h3><ul>{unverified}</ul></div></div></section>'


def _at_a_glance(item):
    labels = (("why", "なぜ必要か"), ("how", "どう対応したか"), ("human_decision", "確認してほしいこと"))
    details = "".join(f'<article class="overview-card"><span>{label}</span><p>{_escape(item[key])}</p></article>' for key, label in labels)
    primary = f'<article class="overview-primary"><span>やったこと</span><p>{_escape(item["what"])}</p></article>'
    return '<section class="overview"><span class="section-num">At a glance</span><h2>変更の要点と確認事項</h2>' + primary + '<div class="overview-details">' + details + "</div></section>"


def _pr_link(url):
    if url is None:
        return ""
    return f'<a class="pr-link" href="{_escape(url)}">PRを開く<span aria-hidden="true"> ↗</span></a>'


def _hero_visual(item):
    if item is None:
        return ""
    return f'<figure class="hero-visual"><div class="visual-head"><span class="tag">ImageGen</span><strong>重要ポイントの説明図</strong></div><img src="{_escape(item["path"])}" alt="{_escape(item["alt"])}"><figcaption>{_escape(item["caption"])}</figcaption></figure>'


def _implementation(items):
    labels = {"high": "重要度: 大", "medium": "重要度: 中", "low": "重要度: 小"}
    ordered = sorted(items, key=lambda item: IMPORTANCE_LEVELS.index(item["importance"]))
    return "".join(f'<article class="card"><div class="card-head"><h3>{_escape(item["title"])}</h3><span class="importance {item["importance"]}">{labels[item["importance"]]}</span></div><p>{_escape(item["body"])}</p></article>' for item in ordered)


def _visuals(items):
    labels = {"actual": "実装画面", "reconstructed": "コードから再構成", "screenshot": "スクリーンショット", "static-explanation": "静的説明"}
    rendered = []
    for item in items:
        path = item.get("path")
        if path and item["type"] in {"actual", "reconstructed"}:
            media = f'<iframe src="{_escape(path)}" title="{_escape(item["title"])}" sandbox="allow-scripts"></iframe>'
        elif path:
            media = f'<img src="{_escape(path)}" alt="{_escape(item["title"])}">'
        else:
            media = '<div class="visual-empty">プレビューはありません</div>'
        rendered.append(f'<figure><div class="visual-head"><span class="tag">{labels[item["type"]]}</span><strong>{_escape(item["title"])}</strong></div>{media}<figcaption>{_escape(item["description"])}</figcaption></figure>')
    return "".join(rendered)


def _flow(flow):
    diagram = ""
    if flow.get("diagram_path"):
        controls = '<div class="diagram-controls"><button type="button" data-zoom="out" aria-label="縮小">−</button><button type="button" data-zoom="reset" class="zoom-level" aria-label="等倍に戻す">100%</button><button type="button" data-zoom="in" aria-label="拡大">＋</button></div>'
        image = f'<img class="diagram" src="{_escape(flow["diagram_path"])}" alt="{_escape(flow["title"])}">'
        diagram = f'<div class="diagram-viewer">{controls}<div class="diagram-pane">{image}</div></div>'
    steps = "".join(f'<div class="flow-row"><span>{_escape(item["condition"])}</span><b aria-hidden="true">→</b><strong>{_escape(item["result"])}</strong></div>' for item in flow["steps"])
    steps = f'<div class="flow">{steps}</div>'
    if diagram:
        steps = f'<details class="flow-steps"><summary>テキスト版フロー</summary>{steps}</details>'
    return f'<h3>{_escape(flow["title"])}</h3><p>{_escape(flow["description"])}</p>{diagram}{steps}'


def _verification(items):
    labels = {"passed": "PASS", "failed": "FAIL", "warning": "注意", "unverified": "未確認"}
    return "".join(f'<div class="check"><span class="status {item["status"]}">{labels[item["status"]]}</span><p><strong>{_escape(item["title"])}</strong><br>{_escape(item["details"])}</p></div>' for item in items)


def _actions(items):
    return "".join(f'<article class="card"><h3>{_escape(item["title"])}</h3><p>{_escape(item["body"])}</p><p class="meta">担当: {_escape(item["owner"])} · {_escape(item["timing"])}</p></article>' for item in items)


def _references(items):
    rows = []
    for item in items:
        label = _escape(item["label"])
        heading = f'<a href="{_escape(item["url"])}">{label}</a>' if item.get("url") else f'<span class="reference-label">{label}（参照不可）</span>'
        rows.append(f'<div class="reference">{heading}<p>{_escape(item["description"])}</p></div>')
    return "".join(rows)


def render(payload, template):
    replacements = {
        "{{TITLE}}": _escape(payload["title"]), "{{SUMMARY}}": _escape(payload["summary"]), "{{PR_LINK}}": _pr_link(payload.get("pr_url")), "{{AT_A_GLANCE}}": _at_a_glance(payload["at_a_glance"]), "{{HERO_VISUAL}}": _hero_visual(payload.get("hero_visual")), "{{RECOMMENDATION}}": _recommendation(payload["recommendation"]),
        "{{DECISIONS}}": _cards(payload["decisions"], "reason") or '<article class="card"><p>この変更に、エージェントが裁量で決めた判断はありません。</p></article>', "{{IMPLEMENTATION}}": _implementation(payload["implementation"]),
        "{{VISUALS}}": _visuals(payload["visuals"]), "{{FLOW}}": _flow(payload["flow"]), "{{VERIFICATION}}": _verification(payload["verification"]),
        "{{CONSTRAINTS}}": "".join(f"<li>{_escape(item)}</li>" for item in payload["constraints"]), "{{NEXT_ACTIONS}}": _actions(payload["next_actions"]), "{{REFERENCES}}": _references(payload["references"]),
    }
    pattern = re.compile(r"{{[A-Z_]+}}")
    unknown = sorted(set(pattern.findall(template)) - set(replacements))
    if unknown:
        raise ContractError(f"template has unresolved markers: {', '.join(unknown)}")
    return pattern.sub(lambda match: replacements[match.group(0)], template)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class _PreviewDependencyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.dependencies: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        tag = tag.lower()
        if tag == "script" and values.get("src"):
            self.dependencies.append(values["src"])
        if tag == "link" and values.get("href"):
            rel = (values.get("rel") or "").lower().split()
            if "stylesheet" not in rel:
                raise ContractError("unsafe preview dependency")
            self.dependencies.append(values["href"])
        if tag == "img" and values.get("src"):
            source = values["src"]
            if not source.lower().startswith("data:image/"):
                self.dependencies.append(source)
        if tag == "a" and values.get("href") and not values["href"].startswith("#"):
            try:
                self.dependencies.append(_relative(values["href"], "preview anchor"))
            except ContractError as error:
                raise ContractError("unsafe preview dependency") from error
        if values.get("style"):
            self.dependencies.extend(_css_dependencies(values["style"]))
        if tag == "style":
            self.in_style = True
        if "srcset" in values:
            raise ContractError("unsafe preview dependency")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.dependencies.extend(_css_dependencies(data))


def _css_dependencies(text: str) -> list[str]:
    values = re.findall(r"url\s*\(\s*(['\"]?)(.*?)\1\s*\)", text, re.IGNORECASE)
    values += re.findall(r"@import\s+(?!url\s*\()(['\"])(.*?)\1", text, re.IGNORECASE)
    dependencies = []
    for _, value in values:
        value = value.strip()
        if value.lower().startswith("data:image/"):
            continue
        try:
            dependencies.append(_relative(value, "CSS dependency"))
        except ContractError as error:
            raise ContractError("unsafe preview dependency") from error
    return dependencies


def _preview_dependencies(text: str) -> list[str]:
    parser = _PreviewDependencyParser()
    try:
        parser.feed(text)
    except (ContractError, ValueError) as error:
        raise ContractError("unsafe preview dependency") from error
    dependencies = []
    for index, value in enumerate(parser.dependencies):
        try:
            dependencies.append(_relative(value, f"preview.dependencies[{index}]"))
        except ContractError as error:
            raise ContractError("unsafe preview dependency") from error
    return dependencies


def _validate_preview(path: Path, reconstructed: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    required = ("コードから再構成した操作デモ", "架空データ・外部通信なし", "aria-live")
    if reconstructed and not all(value in text for value in required):
        raise ContractError("reconstructed preview must identify itself, use fictional data, and include aria-live")
    patterns = (
        r"\b(?:fetch|xmlhttprequest|websocket|eventsource)\s*\(",
        r"\bwindow\s*\.\s*(?:parent|top)\b",
        r"\blocation\b",
        r"\bwindow\s*\.\s*open\s*\(",
        r"\bsetattribute\s*\(",
        r"\bcreateelement\s*\(\s*['\"](?:a|iframe|img|script|link|form)['\"]",
        r"\.\s*(?:href|src|action)\s*=",
        r"https?://",
        r"<\s*meta\b[^>]*\bhttp-equiv\s*=\s*['\"]?\s*refresh\b",
        r"<\s*form\b[^>]*\baction\s*=",
        r"\b(?:src|href)\s*=\s*['\"]?\s*//",
        r"@import\s*(?:url\s*\()?\s*['\"]?\s*//",
        r"url\s*\(\s*['\"]?\s*//",
    )
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
        raise ContractError("unsafe reconstructed preview" if reconstructed else "unsafe HTML preview")
    return _preview_dependencies(text)


def _validate_dependency(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}:
        return []
    if suffix in {".html", ".htm"}:
        return _validate_preview(path, reconstructed=False)
    if suffix not in {".js", ".mjs", ".css"}:
        raise ContractError("unsafe preview dependency")
    text = path.read_text(encoding="utf-8")
    patterns = (
        r"\b(?:fetch|xmlhttprequest|websocket|eventsource|sendbeacon)\s*\(",
        r"https?://",
    )
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
        raise ContractError("unsafe preview dependency")
    if suffix == ".css":
        return _css_dependencies(text)
    module_pattern = re.compile(
        r"(?:\b(?:import|export)\s+(?:[^;]*?\s+from\s*)?|\bimport\s*\(\s*)['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )
    imports = module_pattern.findall(text)
    if re.search(r"\bimport\s*\(", text) and not re.search(r"\bimport\s*\(\s*['\"]", text):
        raise ContractError("unsafe preview dependency")
    if any(not value.startswith(("./", "../")) for value in imports):
        raise ContractError("unsafe preview dependency")
    return imports


def _validate_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text_without_namespaces = re.sub(r"\bxmlns\s*=\s*(['\"])http://www\.w3\.org/2000/svg\1", "", text, flags=re.IGNORECASE)
    patterns = (r"<\s*(?:script|foreignobject)\b", r"\b(?:xlink:)?href\s*=", r"https?://", r"@import\s*(?:url\s*\()?\s*['\"]?\s*(?://|[a-z][a-z0-9+.-]*:)", r"url\s*\(\s*['\"]?\s*(?://|(?!data:(?:font/|application/(?:x-)?font-))[a-z][a-z0-9+.-]*:)", r"<!\s*(?:doctype|entity)\b")
    if any(re.search(pattern, text_without_namespaces, re.IGNORECASE) for pattern in patterns):
        raise ContractError("unsafe SVG")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ContractError("flow diagram must be well-formed SVG") from error
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise ContractError("flow diagram must be well-formed SVG")


def _with_preview_csp(text: str) -> str:
    policy = "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; font-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'; base-uri 'none'"
    meta = f'<meta http-equiv="Content-Security-Policy" content="{policy}">'
    staged, count = re.subn(r"<head(?:\s[^>]*)?>", lambda match: match.group(0) + meta, text, count=1, flags=re.IGNORECASE)
    if count != 1:
        raise ContractError("HTML preview must contain one head element")
    return staged


def _validate_png(path: Path) -> None:
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ContractError("hero_visual must be a valid PNG image")
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ContractError("hero_visual must be a valid PNG image")
    offset = 8
    ihdr = None
    idat_parts = []
    seen_iend = False
    seen_plte = False
    idat_ended = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ContractError("hero_visual must be a valid PNG image")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ContractError("hero_visual must be a valid PNG image")
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ContractError("hero_visual must be a valid PNG image")
        if ihdr is None:
            if kind != b"IHDR" or length != 13:
                raise ContractError("hero_visual must be a valid PNG image")
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IHDR":
            raise ContractError("hero_visual must be a valid PNG image")
        if kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"} and kind[0] & 0x20 == 0:
            raise ContractError("hero_visual must be a valid PNG image")
        if kind == b"PLTE":
            if seen_plte or idat_parts or length == 0 or length % 3 or length > 768:
                raise ContractError("hero_visual must be a valid PNG image")
            seen_plte = True
        if kind == b"IDAT":
            if idat_ended:
                raise ContractError("hero_visual must be a valid PNG image")
            idat_parts.append(payload)
        elif idat_parts and kind != b"IEND":
            idat_ended = True
        if kind == b"IEND":
            if length != 0 or end != len(data) or not idat_parts:
                raise ContractError("hero_visual must be a valid PNG image")
            seen_iend = True
            break
        offset = end
    if ihdr is None or not idat_parts or not seen_iend:
        raise ContractError("hero_visual must be a valid PNG image")
    width, height, depth, color, compression, filter_method, interlace = ihdr
    depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if not width or not height or width > 16384 or height > 16384:
        raise ContractError("hero_visual must be a valid PNG image")
    if abs(width * 9 - height * 16) * 100 > width * 9:
        raise ContractError("hero_visual must use an approximately 16:9 PNG image")
    if color not in depths or depth not in depths[color] or compression != 0 or filter_method != 0 or interlace not in {0, 1}:
        raise ContractError("hero_visual must be a valid PNG image")
    if (color == 3 and not seen_plte) or (color in {0, 4} and seen_plte):
        raise ContractError("hero_visual must be a valid PNG image")
    passes = [(0, 0, 1, 1)] if interlace == 0 else [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    layout = []
    for start_x, start_y, step_x, step_y in passes:
        pass_width = 0 if width <= start_x else (width - start_x + step_x - 1) // step_x
        pass_height = 0 if height <= start_y else (height - start_y + step_y - 1) // step_y
        layout.append((pass_height, (pass_width * channels[color] * depth + 7) // 8))
    expected = sum(rows * (row_bytes + 1) for rows, row_bytes in layout)
    if expected > 256 * 1024 * 1024:
        raise ContractError("hero_visual must be a valid PNG image")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(b"".join(idat_parts), expected + 1)
    if len(raw) > expected or decoder.unconsumed_tail:
        raise ContractError("hero_visual must be a valid PNG image")
    raw += decoder.flush(expected + 1 - len(raw))
    if not decoder.eof or decoder.unused_data or len(raw) != expected:
        raise ContractError("hero_visual must be a valid PNG image")
    raw_offset = 0
    for rows, row_bytes in layout:
        for _ in range(rows):
            if raw[raw_offset] > 4:
                raise ContractError("hero_visual must be a valid PNG image")
            raw_offset += row_bytes + 1


def _stage(relative: str, source_root: Path, output_root: Path, kind: str) -> list[str]:
    candidate = source_root / relative
    path_parts = PurePosixPath(relative).parts
    if any((source_root.joinpath(*path_parts[:index])).is_symlink() for index in range(1, len(path_parts) + 1)):
        raise ContractError(f"asset not found or unsafe: {relative}")
    source = candidate.resolve()
    if not _inside(source, source_root) or not source.is_file():
        raise ContractError(f"asset not found or unsafe: {relative}")
    staged_text = None
    dependencies: list[str] = []
    if kind in {"actual", "reconstructed"} and source.suffix.lower() in {".html", ".htm"}:
        dependencies = _validate_preview(source, reconstructed=kind == "reconstructed")
        staged_text = _with_preview_csp(source.read_text(encoding="utf-8"))
    elif kind == "preview-dependency" and source.suffix.lower() in {".html", ".htm"}:
        dependencies = _validate_dependency(source)
        staged_text = _with_preview_csp(source.read_text(encoding="utf-8"))
    elif kind == "preview-dependency":
        dependencies = _validate_dependency(source)
    elif kind == "svg":
        _validate_svg(source)
    elif kind == "hero-visual":
        _validate_png(source)
    target = output_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not _inside(target.parent.resolve(), output_root) or target.is_symlink():
        raise ContractError(f"unsafe output asset: {relative}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        if staged_text is None:
            shutil.copy2(source, temporary)
        else:
            temporary.write_text(staged_text, encoding="utf-8")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return dependencies


def stage_assets(payload, input_path, output_path):
    source_root = input_path.resolve().parent
    output_root = output_path.resolve().parent
    output_root.mkdir(parents=True, exist_ok=True)
    prefix = PurePosixPath(".story-assets") if source_root == output_root else PurePosixPath()
    staging_root = output_root / prefix
    if payload.get("hero_visual"):
        original_path = payload["hero_visual"]["path"]
        _stage(original_path, source_root, staging_root, "hero-visual")
        payload["hero_visual"]["path"] = (prefix / original_path).as_posix()
    for item in payload["visuals"]:
        if item.get("path"):
            original_path = item["path"]
            dependencies = _stage(original_path, source_root, staging_root, item["type"])
            preview_parent = PurePosixPath(original_path).parent
            pending = [(preview_parent, dependency) for dependency in dependencies]
            staged_dependencies: set[str] = set()
            while pending:
                dependency_parent, dependency = pending.pop()
                dependency_path = posixpath.normpath((dependency_parent / dependency).as_posix())
                try:
                    dependency_path = _relative(dependency_path, "preview dependency")
                except ContractError as error:
                    raise ContractError("unsafe preview dependency") from error
                if dependency_path in staged_dependencies:
                    continue
                staged_dependencies.add(dependency_path)
                nested = _stage(dependency_path, source_root, staging_root, "preview-dependency")
                nested_parent = PurePosixPath(dependency_path).parent
                pending.extend((nested_parent, item) for item in nested)
            item["path"] = (prefix / original_path).as_posix()
    if payload["flow"].get("diagram_path"):
        original_path = payload["flow"]["diagram_path"]
        _stage(original_path, source_root, staging_root, "svg")
        payload["flow"]["diagram_path"] = (prefix / original_path).as_posix()
    for item in payload["references"]:
        reference = item.get("url")
        if reference and not urlparse(reference).scheme:
            _stage(reference, source_root, staging_root, "reference")
            item["url"] = (prefix / reference).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        payload = validate_payload(json.loads(args.input.read_text(encoding="utf-8")))
        template = (Path(__file__).resolve().parents[1] / "templates/story.html").read_text(encoding="utf-8")
        stage_assets(payload, args.input, args.output)
        page = render(payload, template)
        temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
        temporary.write_text(page, encoding="utf-8")
        temporary.replace(args.output)
        if args.open:
            command = ["open", str(args.output.resolve())] if sys.platform == "darwin" else ["xdg-open", str(args.output.resolve())]
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                if result.returncode:
                    print(result.stderr.strip() or "failed to open output", file=sys.stderr)
            except OSError:
                print("failed to open output", file=sys.stderr)
    except (ContractError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"render_story: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
