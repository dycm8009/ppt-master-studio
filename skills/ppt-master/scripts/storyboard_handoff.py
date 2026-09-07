#!/usr/bin/env python3
"""
PPT Master - Storyboard Handoff

Build a read-only Storyboard projection from a validated Design Spec. The
Design Spec remains the sole authority; this helper creates no confirmation
gate and never mutates ``design_spec.md``.

Usage:
    python3 scripts/storyboard_handoff.py build <project_path>
    python3 scripts/storyboard_handoff.py status <project_path>

Examples:
    python3 scripts/storyboard_handoff.py build projects/example

Dependencies:
    None (only uses standard library)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from console_encoding import configure_utf8_stdio  # noqa: E402

SCHEMA = "ppt-master-storyboard-projection/v1"
HANDOFF_SCHEMA = "ppt-master-storyboard-handoff/v1"
SLIDE_RE = re.compile(r"^####\s+Slide\s+(\d+)\s*-\s*(.+?)\s*$", re.IGNORECASE)
PART_RE = re.compile(r"^###\s+Part\s+\d+\s*:\s*(.+?)\s*$", re.IGNORECASE)
FIELD_RE = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean(value: str) -> str:
    return value.strip("\r\n")


def _structural_lines(lines: list[str]) -> list[str]:
    """Mask fenced examples without changing their literal content."""
    result = []
    fence = None
    for line in lines:
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            result.append("")
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
        elif match:
            fence = match[1]
            result.append("")
        else:
            result.append(line)
    if fence:
        raise RuntimeError("unclosed code fence in Design Spec; repair the source")
    return result


def _parse_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line, structural in zip(lines, _structural_lines(lines)):
        match = FIELD_RE.match(structural)
        if match:
            current = match.group(1).strip()
            if current in fields:
                raise RuntimeError(f"duplicate Storyboard field: {current}")
            fields[current] = [match.group(2).strip()]
            continue
        if current is not None:
            fields[current].append(line)
    return {key: _clean("\n".join(value)) for key, value in fields.items()}


def _risk_tags(fields: dict[str, str]) -> list[str]:
    tags: set[str] = set()
    content = fields.get("Content", "")
    combined = "\n".join(fields.values())
    viz = fields.get("Visualization", "")
    native = fields.get("Native-ready", "")
    if len(content) >= 650 or content.count("\n") >= 6:
        tags.add("dense-content")
    if viz or native:
        tags.add("visualization")
    if re.search(r"\b(chart|table)\b|图表|表格|数据图", f"{viz}\n{content}", re.IGNORECASE):
        tags.add("chart-or-table")
    if fields.get("Images"):
        tags.add("images")
    if fields.get("Mathematical content"):
        tags.add("formula")
    if fields.get("Motion suggestion"):
        tags.add("motion")
    if fields.get("Fact IDs"):
        tags.add("source-sensitive")
    if re.search(r"```|~~~|(?<!\w)C\+\+(?!\w)|\b(code|snippet|function|class|API)\b|代码", combined, re.IGNORECASE):
        tags.add("code-or-api")
    return sorted(tags)


def parse_design_spec(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"design_spec.md missing: {path}")
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    structural = _structural_lines(lines)
    try:
        ix = next(i for i, line in enumerate(structural) if line.strip() == "## IX. Content Outline")
    except StopIteration as exc:
        raise RuntimeError("Design Spec is missing `## IX. Content Outline`") from exc
    end = next(
        (i for i in range(ix + 1, len(lines)) if structural[i].startswith("## X.")),
        len(lines),
    )

    slides: list[dict[str, Any]] = []
    current_part = ""
    i = ix + 1
    while i < end:
        part_match = PART_RE.match(structural[i])
        if part_match:
            current_part = part_match.group(1).strip()
            i += 1
            continue
        slide_match = SLIDE_RE.match(structural[i])
        if not slide_match:
            i += 1
            continue
        number = int(slide_match.group(1))
        header_name = slide_match.group(2).strip()
        block: list[str] = []
        i += 1
        while i < end and not SLIDE_RE.match(structural[i]) and not PART_RE.match(structural[i]):
            block.append(lines[i])
            i += 1
        fields = _parse_fields(block)
        title = fields.get("Title") or header_name
        slide = {
            "slide_id": f"P{number:02d}",
            "ordinal": len(slides) + 1,
            "source_number": number,
            "section": current_part or None,
            "header_name": header_name,
            "title": title,
            "audience_move": fields.get("Audience move", ""),
            "core_message": fields.get("Core message", ""),
            "layout": fields.get("Layout", ""),
            "content": fields.get("Content", ""),
            "evidence": fields.get("Fact IDs", ""),
            "visualization": fields.get("Visualization", ""),
            "images": fields.get("Images", ""),
            "mathematical_content": fields.get("Mathematical content", ""),
            "motion_suggestion": fields.get("Motion suggestion", ""),
            "native_ready": fields.get("Native-ready", ""),
            "risk_tags": _risk_tags(fields),
            "fields": fields,
        }
        slides.append(slide)

    if not slides:
        raise RuntimeError("Design Spec §IX contains no `#### Slide NN - ...` blocks")
    numbers = [slide["source_number"] for slide in slides]
    if any(number < 1 for number in numbers) or len(set(numbers)) != len(numbers):
        raise RuntimeError("duplicate or invalid page identity in Design Spec")
    counts_in_spec = re.findall(r"^\|\s*Page Count\s*\|\s*(\d+)\s*\|", "\n".join(structural[:ix]), re.M)
    if counts_in_spec and (len(counts_in_spec) != 1 or int(counts_in_spec[0]) != len(slides)):
        raise RuntimeError("Design Spec Page Count does not match the page roster")
    for index, slide in enumerate(slides):
        slide["previous_slide"] = slides[index - 1]["slide_id"] if index else None
        slide["next_slide"] = slides[index + 1]["slide_id"] if index + 1 < len(slides) else None
    counts = Counter(tag for slide in slides for tag in slide["risk_tags"])
    return {
        "schema": SCHEMA,
        "design_spec_sha256": hashlib.sha256(raw).hexdigest(),
        "slide_count": len(slides),
        "risk_counts": dict(sorted(counts.items())),
        "slides": slides,
    }


def _page_html(storyboard: dict[str, Any]) -> str:
    payload = json.dumps(storyboard, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PPT Master Studio · Storyboard</title>
<style>
:root{{--bg:#0b1020;--panel:#121a2b;--line:#2d3b52;--text:#dbe6f5;--muted:#8fa1b8;--accent:#65a9ff;--risk:#ffbd66}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Inter,"Noto Sans CJK SC",system-ui,sans-serif}}
#app{{height:100vh;display:grid;grid-template-columns:260px minmax(0,1fr)}} aside{{background:var(--panel);border-right:1px solid var(--line);overflow:auto}} main{{overflow:auto;padding:28px}}
.header{{padding:18px;border-bottom:1px solid var(--line);font-weight:750}} .meta{{font-size:12px;color:var(--muted);margin-top:5px}} #list{{padding:10px}}
.item{{width:100%;text-align:left;border:1px solid transparent;background:transparent;color:var(--text);padding:10px;border-radius:8px;margin:3px 0;cursor:pointer}} .item:hover,.item.active{{background:#19253b;border-color:#334762}} .section{{font-size:11px;color:var(--muted)}}
.card{{max-width:1100px;margin:0 auto;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px}} h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:13px;color:var(--accent);margin:22px 0 7px;text-transform:uppercase;letter-spacing:.05em}} .value{{white-space:pre-wrap}} .muted{{color:var(--muted)}} .tags{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}} .tag{{border:1px solid #705f3c;color:var(--risk);padding:3px 7px;border-radius:999px;font-size:11px}} .flow{{display:flex;gap:8px;margin-top:20px}} .flow button{{border:1px solid #3e526f;background:#18243a;color:var(--text);padding:7px 10px;border-radius:7px;cursor:pointer}} .flow button:disabled{{opacity:.35}}
@media(max-width:700px){{#app{{height:auto;display:block}}aside{{max-height:220px}}main{{padding:12px}}.card{{padding:16px;overflow-wrap:anywhere}}}}
</style></head>
<body><div id="app"><aside><div class="header">Storyboard<div class="meta" id="summary"></div></div><div id="list"></div></aside><main><div class="card" id="card"></div></main></div>
<script>
const data={payload}; let index=0; const $=id=>document.getElementById(id);
function esc(s){{return String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function row(label,value){{return value?`<h2>${{esc(label)}}</h2><div class="value">${{esc(value)}}</div>`:''}}
function renderList(){{$('list').innerHTML=data.slides.map((s,i)=>`<button class="item ${{i===index?'active':''}}" data-i="${{i}}"><div>${{esc(s.slide_id)}} · ${{esc(s.title)}}</div><div class="section">${{esc(s.section||'')}}</div></button>`).join('');document.querySelectorAll('.item').forEach(b=>b.onclick=()=>{{index=Number(b.dataset.i);render()}})}}
function render(){{const s=data.slides[index];const tags=s.risk_tags.map(t=>`<span class="tag">${{esc(t)}}</span>`).join('');$('card').innerHTML=`<div class="muted">${{esc(s.section||'')}} · ${{s.ordinal}} / ${{data.slide_count}}</div><h1>${{esc(s.title)}}</h1>${{row('Audience move',s.audience_move)}}${{row('Core message',s.core_message)}}${{row('Evidence / source dependency',s.evidence)}}${{row('Layout / visual focus',s.layout)}}${{row('Visualization',s.visualization)}}${{row('Images',s.images)}}${{row('Content',s.content)}}${{row('Mathematical content',s.mathematical_content)}}${{row('Motion suggestion',s.motion_suggestion)}}${{tags?`<h2>Risk hints</h2><div class="tags">${{tags}}</div>`:''}}<div class="flow"><button id="prev">‹ 上一页</button><button id="next">下一页 ›</button></div>`;$('prev').disabled=index===0;$('next').disabled=index===data.slides.length-1;$('prev').onclick=()=>{{index--;render()}};$('next').onclick=()=>{{index++;render()}};renderList()}}
$('summary').textContent=`${{data.slide_count}} 页 · 只读快照 ${{data.design_spec_sha256.slice(0,12)}}`;render();
</script></body></html>'''


def build(project: Path) -> dict[str, Any]:
    project = project.resolve()
    spec = project / "design_spec.md"
    storyboard = parse_design_spec(spec)
    runtime = project / "live_preview"
    runtime.mkdir(parents=True, exist_ok=True)
    json_path = runtime / "storyboard.json"
    html_path = runtime / "storyboard.html"
    page = _page_html(storyboard)
    storyboard["html_sha256"] = hashlib.sha256(page.encode("utf-8")).hexdigest()
    from review_io import write_text_atomic
    write_text_atomic(html_path, page)
    write_text_atomic(json_path, json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n")
    return {
        "schema": HANDOFF_SCHEMA,
        "surface": "storyboard",
        "status": "ready",
        "authority": "design-spec-read-only-projection",
        "design_spec_sha256": storyboard["design_spec_sha256"],
        "slide_count": storyboard["slide_count"],
        "risk_counts": storyboard["risk_counts"],
        "launch_path": str(html_path),
        "manifest_path": str(json_path),
        "blocking": False,
        "interaction_state": {
            "generated": True,
            "launch_ready": True,
            "access_provided": None,
            "user_submitted": False,
            "validated": False,
            "applied": False,
            "stale": False,
            "next_action": "optional-read-only-review",
        },
    }


def load_current(project: Path) -> dict[str, Any]:
    """Read the current derived pair; never treat a changed projection as authority."""
    project = project.resolve()
    runtime = project / "live_preview"
    try:
        value = json.loads((runtime / "storyboard.json").read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schema") != SCHEMA:
            raise RuntimeError("unsupported Storyboard schema; rebuild Storyboard")
        expected = parse_design_spec(project / "design_spec.md")
        if {k: v for k, v in value.items() if k != "html_sha256"} != expected:
            raise RuntimeError("stale or modified Storyboard; rebuild from the current Design Spec")
        if not (runtime / "storyboard.html").is_file():
            raise RuntimeError("Storyboard HTML missing; rebuild Storyboard")
        if value.get("html_sha256") and value["html_sha256"] != _sha(runtime / "storyboard.html"):
            raise RuntimeError("Storyboard HTML changed; rebuild Storyboard")
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        raise RuntimeError(f"invalid Storyboard: {exc}; rebuild Storyboard") from exc


def status(project: Path) -> dict[str, Any]:
    project = project.resolve()
    manifest = project / "live_preview/storyboard.json"
    if not manifest.is_file():
        return {"schema": HANDOFF_SCHEMA, "surface": "storyboard", "status": "missing", "stale": False}
    try:
        value = load_current(project)
    except RuntimeError as exc:
        return {"schema": HANDOFF_SCHEMA, "surface": "storyboard", "status": "stale", "stale": True,
                "error": str(exc)}
    return {"schema": HANDOFF_SCHEMA, "surface": "storyboard", "status": "current", "stale": False,
            "design_spec_sha256": value["design_spec_sha256"], "slide_count": value["slide_count"]}


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build/read PPT Master Design Spec Storyboard projection")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("project", type=Path)
    s = sub.add_parser("status")
    s.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.project) if args.command == "build" else status(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"storyboard_handoff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
