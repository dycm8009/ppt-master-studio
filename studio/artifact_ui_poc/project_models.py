from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
from html import unescape
from pathlib import Path
from typing import Any

from studio.static_ui.assets import catalogs
from studio.static_ui.base import digest, localized, read_json, value_of
from studio.static_ui.review import rewrite_svg_for_static
from studio.static_ui.templates import build_template_options, template_display


PROSE_FIELDS = (
    "audience",
    "communication_intent",
    "audience_outcome",
    "core_message",
    "delivery_context",
    "artifact_afterlife",
    "content_divergence",
)
TEMPLATE_KINDS = ("brand", "style", "layout", "deck")
XML_DECL_RE = re.compile(r"<\?xml[^>]*>\s*")
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
EVENT_ATTR_RE = re.compile(r"\s+on[a-zA-Z0-9_-]+\s*=\s*([\"']).*?\1", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(
    r"(?P<prefix>\b(?:href|xlink:href)\s*=\s*)(?P<quote>[\"'])(?P<ref>[^\"']+)(?P=quote)",
    re.IGNORECASE,
)
ID_RE = re.compile(r"\bid\s*=\s*([\"'])([^\"']+)\1")


def _strip_xml_decl(svg: str) -> str:
    return XML_DECL_RE.sub("", svg)


def _sanitize_svg_for_artifact(svg: str) -> tuple[str, dict[str, int]]:
    without_scripts, script_count = SCRIPT_RE.subn("", svg)
    inert, event_count = EVENT_ATTR_RE.subn("", without_scripts)
    return inert, {
        "removed_script_blocks": script_count,
        "removed_event_handlers": event_count,
    }


def stage1_artifact_model(project: Path) -> dict[str, Any]:
    project = project.resolve()
    rec = read_json(project / "confirm_ui" / "recommendations.stage1.json")
    if rec.get("stage") != "stage1":
        raise ValueError("recommendations.stage1.json does not declare stage1")

    opts, _ = build_template_options(project)
    lang = str(rec.get("primary_language") or opts.get("lang") or "zh-CN")
    catalog = catalogs()
    recommended_canvas = str((rec.get("recommend") or {}).get("canvas") or "ppt169")

    canvases = []
    for item in catalog.get("canvas", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        canvases.append(
            {
                "id": str(item["id"]),
                "label": localized(item, lang, str(item["id"])),
                "dim": str(item.get("dim") or ""),
                "recommended": str(item["id"]) == recommended_canvas,
            }
        )

    library: dict[str, list[dict[str, Any]]] = {}
    for kind in TEMPLATE_KINDS:
        rows = []
        for candidate in opts.get("library", {}).get(kind, []):
            name, summary = template_display(kind, candidate, lang)
            rows.append(
                {
                    "key": candidate["key"],
                    "kind": kind,
                    "source": "library",
                    "id": candidate.get("id"),
                    "label": name,
                    "summary": summary,
                }
            )
        library[kind] = rows

    explicit_groups: dict[str, dict[str, Any]] = {}
    for candidate in opts.get("explicit", []):
        root = str(candidate.get("workspace_root") or "")
        group = explicit_groups.setdefault(
            root,
            {
                "workspace_root": root,
                "label": str(candidate.get("label") or Path(root).name or root),
                "selection_keys": [],
                "kinds": [],
            },
        )
        group["selection_keys"].append(candidate["key"])
        group["kinds"].append(candidate["kind"])

    fields = {key: str(value_of(rec, key, "")) for key in PROSE_FIELDS}
    fields["primary_language"] = str(rec.get("primary_language") or lang)
    fields["canvas"] = recommended_canvas

    return {
        "schema": "ppt-master-chat-inline-stage1-model/v1",
        "surface": "stage1",
        "language": lang,
        "fields": fields,
        "field_order": list(PROSE_FIELDS),
        "canvases": canvases,
        "template": {
            "default_mode": opts["default_mode"],
            "library": library,
            "explicit_groups": list(explicit_groups.values()),
            "preselected_keys": list(opts.get("preselected_keys") or []),
        },
        "recommendation_sha256": digest(rec),
        "options_sha256": opts["options_sha256"],
        "authority": {
            "capture_schema": "ppt-master-chat-confirm/v1",
            "accepted_schema": "ppt-master-static-ui-accepted/v1",
            "validator": "studio/scripts/static_ui_adapter.py validate",
        },
    }


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_local_asset(project: Path, svg_path: Path, ref: str) -> Path | None:
    decoded = unescape(ref)
    raw = Path(decoded)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend((project / raw, svg_path.parent / raw))
    for candidate in candidates:
        resolved = candidate.resolve()
        if _inside(resolved, project) and resolved.is_file():
            return resolved
    return None


def _data_uri(path: Path) -> tuple[str, int]:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime.startswith("image/"):
        raise ValueError(f"artifact SVG asset is not an image: {path}")
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}", len(raw)


def inline_svg_assets(
    svg: str,
    *,
    project: Path,
    svg_path: Path,
    max_total_asset_bytes: int = 6 * 1024 * 1024,
) -> tuple[str, dict[str, Any]]:
    total = 0
    count = 0
    issues: list[str] = []
    cache: dict[Path, tuple[str, int]] = {}

    def repl(match: re.Match[str]) -> str:
        nonlocal total, count
        prefix, quote, ref = match.group("prefix"), match.group("quote"), match.group("ref")
        if re.match(r"^(?:data:|#)", ref, re.IGNORECASE):
            return match.group(0)
        if re.match(r"^https?://", ref, re.IGNORECASE):
            issues.append(f"remote SVG asset is not self-contained in {svg_path.name}: {ref}")
            return match.group(0)
        if ref.lower().startswith("file:"):
            issues.append(f"unsupported file URI in {svg_path.name}: {ref}")
            return match.group(0)
        asset = _resolve_local_asset(project, svg_path, ref)
        if asset is None:
            issues.append(f"unresolved local asset in {svg_path.name}: {ref}")
            return match.group(0)
        if asset not in cache:
            try:
                cache[asset] = _data_uri(asset)
            except ValueError as exc:
                issues.append(str(exc))
                return match.group(0)
        uri, size = cache[asset]
        if total + size > max_total_asset_bytes:
            issues.append(
                f"asset inline budget exceeded ({max_total_asset_bytes} bytes) at {asset.relative_to(project)}"
            )
            return match.group(0)
        total += size
        count += 1
        return f"{prefix}{quote}{uri}{quote}"

    rendered = HREF_RE.sub(repl, svg)
    return rendered, {
        "embedded_asset_refs": count,
        "embedded_asset_bytes": total,
        "issues": issues,
        "artifact_renderable": not issues,
    }


def deck_review_artifact_model(
    project: Path,
    *,
    max_total_asset_bytes_per_slide: int = 6 * 1024 * 1024,
) -> dict[str, Any]:
    project = project.resolve()
    svg_paths = sorted((project / "svg_output").glob("*.svg"))
    if not svg_paths:
        raise ValueError("svg_output/*.svg is required for deck review")

    slides: list[dict[str, Any]] = []
    validator_roster: list[tuple[str, str]] = []
    all_issues: list[str] = []

    for path in svg_paths:
        original = path.read_text(encoding="utf-8", errors="replace")
        validator_svg = _strip_xml_decl(rewrite_svg_for_static(original))
        validator_svg_sha256 = hashlib.sha256(validator_svg.encode("utf-8")).hexdigest()
        validator_roster.append((path.name, validator_svg_sha256))

        artifact_source, sanitization = _sanitize_svg_for_artifact(_strip_xml_decl(original))
        artifact_svg, asset_info = inline_svg_assets(
            artifact_source,
            project=project,
            svg_path=path,
            max_total_asset_bytes=max_total_asset_bytes_per_slide,
        )
        asset_info.update(sanitization)
        all_issues.extend(asset_info["issues"])
        element_ids = []
        seen = set()
        for _quote, element_id in ID_RE.findall(artifact_svg):
            if element_id not in seen:
                seen.add(element_id)
                element_ids.append(element_id)

        slides.append(
            {
                "file": path.name,
                "stem": path.stem,
                "svg": artifact_svg,
                "source_svg_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                "validator_svg_sha256": validator_svg_sha256,
                "editable_element_ids": element_ids,
                "asset_info": asset_info,
            }
        )

    return {
        "schema": "ppt-master-chat-inline-deck-review-model/v1",
        "surface": "deck-review",
        "slides": slides,
        "svg_roster_sha256": digest(validator_roster),
        "artifact_renderable": not all_issues,
        "issues": all_issues,
        "authority": {
            "capture_schema": "ppt-master-static-deck-review-response/v1",
            "accepted_schema": "ppt-master-static-ui-accepted/v1",
            "validator": "studio/scripts/static_ui_adapter.py validate",
            "roster_hash_semantics": "identical-to-studio.static_ui.review.deck_review_html",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chat-inline artifact models from a PPT Master project")
    parser.add_argument("surface", choices=("stage1", "deck-review"))
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    model = (
        stage1_artifact_model(args.project)
        if args.surface == "stage1"
        else deck_review_artifact_model(args.project)
    )
    print(json.dumps(model, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
