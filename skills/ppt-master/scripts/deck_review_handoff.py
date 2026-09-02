#!/usr/bin/env python3
"""Framework-free per-slide Deck Review handoff for PPT Master Studio.

Builds a self-contained HTML review surface from the project's real SVG files.
The user reviews every page, marks it approved or requests changes, and copies
one JSON response back to the host.  No Flask server or local HTTP listener is
required.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RESPONSE_SCHEMA = "ppt-master-static-deck-review-response/v1"
MANIFEST_SCHEMA = "ppt-master-static-deck-review-manifest/v1"
RECEIPT_SCHEMA = "ppt-master-static-deck-review-receipt/v1"
SURFACE = "deck-review"


def _slide_files(project: Path) -> list[Path]:
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        raise RuntimeError(f"svg_output missing: {svg_dir}")
    files = sorted(
        (p for p in svg_dir.iterdir() if p.is_file() and p.suffix.lower() == ".svg"),
        key=lambda p: p.name,
    )
    if not files:
        raise RuntimeError(f"no SVG slides found: {svg_dir}")
    return files


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _roster(files: list[Path]) -> tuple[list[dict[str, Any]], str]:
    rows = []
    for index, path in enumerate(files, start=1):
        raw = path.read_bytes()
        rows.append({"slide": path.name, "ordinal": index, "sha256": _sha256_bytes(raw)})
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return rows, _sha256_bytes(canonical)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _sanitized_svg(path: Path) -> str:
    """Return browser-review SVG while removing executable SVG constructs."""
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError(f"failed to parse {path.name}: {exc}") from exc
    root = tree.getroot()
    if _local(root.tag) != "svg":
        raise RuntimeError(f"not an SVG root: {path.name}")

    def scrub(parent: ET.Element) -> None:
        for child in list(parent):
            if _local(child.tag) in {"script", "foreignobject"}:
                parent.remove(child)
                continue
            for key in list(child.attrib):
                lower = key.lower()
                value = str(child.attrib.get(key) or "")
                if lower.startswith("on") or re.search(r"javascript\s*:", value, re.IGNORECASE):
                    child.attrib.pop(key, None)
            scrub(child)

    for key in list(root.attrib):
        if key.lower().startswith("on"):
            root.attrib.pop(key, None)
    scrub(root)
    root.set("data-ppt-master-review-slide", path.name)
    root.set("style", "max-width:100%;max-height:100%;display:block;margin:auto")
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _page_html(slides: list[dict[str, Any]], roster_hash: str) -> str:
    slide_json = json.dumps(slides, ensure_ascii=False).replace("</", "<\\/")
    roster_json = json.dumps(roster_hash)
    schema_json = json.dumps(RESPONSE_SCHEMA)
    surface_json = json.dumps(SURFACE)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PPT Master Studio · Deck Review</title>
<style>
:root{{--bg:#0b1020;--panel:#121a2b;--line:#2c3950;--text:#d7e2f0;--muted:#8fa1b8;--blue:#5ea8ff;--amber:#ffb84d;--green:#5dd6c0;--red:#ff7a7a}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,"Noto Sans CJK SC",system-ui,sans-serif}}
#app{{height:100vh;display:grid;grid-template-columns:230px minmax(0,1fr) 330px}}
.panel{{background:var(--panel);border-color:var(--line)}} #left{{border-right:1px solid var(--line);overflow:auto}} #right{{border-left:1px solid var(--line);padding:18px;overflow:auto}}
.header{{padding:16px 18px;border-bottom:1px solid var(--line);font-weight:700}} #progress{{font-size:12px;color:var(--muted);margin-top:4px}}
#list{{padding:10px}} .slide-btn{{width:100%;display:flex;gap:8px;align-items:center;text-align:left;padding:9px 10px;margin:4px 0;border:1px solid transparent;border-radius:8px;background:transparent;color:var(--text);cursor:pointer}}
.slide-btn:hover,.slide-btn.active{{background:#18243a;border-color:#32445f}} .dot{{width:9px;height:9px;border-radius:50%;background:#506079;flex:0 0 auto}} .approved .dot{{background:var(--green)}} .changes .dot{{background:var(--amber)}}
#center{{min-width:0;display:flex;flex-direction:column}} #nav{{height:56px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:center;gap:14px}} #nav button,#actions button,#copy-area button{{border:1px solid #425673;background:#18243a;color:var(--text);border-radius:8px;padding:8px 12px;cursor:pointer}}
#nav button:disabled,#actions button:disabled{{opacity:.4;cursor:not-allowed}} #slide-name{{min-width:180px;text-align:center;color:var(--muted)}}
#canvas-wrap{{flex:1;min-height:0;padding:24px;display:flex;align-items:center;justify-content:center;overflow:auto}} #canvas{{width:min(100%,1280px);aspect-ratio:16/9;background:#fff;box-shadow:0 14px 50px rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;overflow:hidden}}
.review-title{{font-size:18px;font-weight:750;margin:0 0 8px}} .review-note{{color:var(--muted);font-size:12px;margin-bottom:18px}} .choice{{display:block;border:1px solid var(--line);border-radius:9px;padding:12px;margin:10px 0;cursor:pointer}} .choice input{{margin-right:8px}}
textarea{{width:100%;min-height:130px;resize:vertical;border:1px solid #425673;border-radius:8px;background:#0d1525;color:var(--text);padding:10px;font:inherit}} #actions{{display:grid;gap:9px;margin-top:14px}} #save-next{{background:#1f5f97!important;border-color:var(--blue)!important}} #complete{{background:#235d50!important;border-color:var(--green)!important;font-weight:700}}
#copy-area{{display:none;margin-top:18px;padding-top:16px;border-top:1px solid var(--line)}} #result-json{{min-height:210px;font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}} .error{{color:var(--red)}} .ok{{color:var(--green)}}
</style>
</head>
<body>
<div id="app">
  <section id="left" class="panel"><div class="header">逐页 Review<div id="progress"></div></div><div id="list"></div></section>
  <main id="center"><div id="nav"><button id="prev">‹ 上一页</button><span id="slide-name"></span><button id="next">下一页 ›</button></div><div id="canvas-wrap"><div id="canvas"></div></div></main>
  <aside id="right" class="panel">
    <h2 class="review-title">本页结论</h2>
    <div class="review-note">这里渲染的是原始 SVG，不是截图。每一页都必须明确选择一次；有修改意见时请写具体。</div>
    <label class="choice"><input type="radio" name="decision" value="approved">通过</label>
    <label class="choice"><input type="radio" name="decision" value="changes">需要修改</label>
    <textarea id="comment" placeholder="例如：P07 右侧因果链太密，保留结论但把日志证据拆成上下两层。"></textarea>
    <div id="status"></div>
    <div id="actions"><button id="save-next">保存本页并到下一页</button><button id="complete" disabled>完成逐页 Review</button></div>
    <div id="copy-area"><h3>Review JSON 已生成</h3><div class="review-note">复制下面 JSON 原样粘贴回 ChatGPT。页面不会自动关闭。</div><textarea id="result-json" readonly></textarea><button id="copy">复制 Review JSON</button></div>
  </aside>
</div>
<script>
const slides={slide_json}; const rosterHash={roster_json}; const responseSchema={schema_json}; const surface={surface_json};
let index=0; const reviews={{}};
const $=id=>document.getElementById(id); const list=$('list'), canvas=$('canvas'), status=$('status'), comment=$('comment');
function reviewedCount(){{return Object.keys(reviews).length}}
function renderList(){{list.innerHTML='';slides.forEach((s,i)=>{{const b=document.createElement('button');b.className='slide-btn '+(i===index?'active ':'')+(reviews[s.slide]?.decision||'');b.innerHTML=`<span class="dot"></span><span>${{String(s.ordinal).padStart(2,'0')}} · ${{s.slide}}</span>`;b.onclick=()=>{{saveDraft();index=i;render()}};list.appendChild(b)}})}}
function loadReview(){{const s=slides[index],r=reviews[s.slide]||{{}};document.querySelectorAll('input[name=decision]').forEach(x=>x.checked=x.value===r.decision);comment.value=r.comment||'';comment.disabled=r.decision!=='changes';}}
function saveDraft(strict=false){{const s=slides[index];const selected=document.querySelector('input[name=decision]:checked');if(!selected){{if(strict)throw new Error('请先选择“通过”或“需要修改”');return}}const decision=selected.value;const text=comment.value.trim();if(decision==='changes'&&!text){{if(strict)throw new Error('选择“需要修改”时必须填写修改意见');return}}reviews[s.slide]={{decision,comment:decision==='changes'?text:''}};}}
function render(){{const s=slides[index];$('complete').textContent=`完成 ${{slides.length}} 页 Review`;$('slide-name').textContent=`${{s.ordinal}} / ${{slides.length}} · ${{s.slide}}`;$('prev').disabled=index===0;$('next').disabled=index===slides.length-1;canvas.innerHTML=s.svg;loadReview();renderList();$('progress').textContent=`已确认 ${{reviewedCount()}} / ${{slides.length}}`;$('complete').disabled=reviewedCount()!==slides.length;status.textContent='';}}
document.querySelectorAll('input[name=decision]').forEach(x=>x.onchange=()=>{{comment.disabled=x.value!=='changes';if(x.value==='approved')comment.value='';}});
$('prev').onclick=()=>{{saveDraft();if(index>0){{index--;render()}}}};$('next').onclick=()=>{{saveDraft();if(index<slides.length-1){{index++;render()}}}};
$('save-next').onclick=()=>{{try{{saveDraft(true);render();if(index<slides.length-1){{index++;render()}}status.textContent='本页已记录';status.className='ok'}}catch(e){{status.textContent=e.message;status.className='error'}}}};
$('complete').onclick=()=>{{try{{saveDraft(true);if(reviewedCount()!==slides.length)throw new Error('仍有页面没有确认');const changes=slides.filter(s=>reviews[s.slide].decision==='changes').map(s=>({{slide:s.slide,ordinal:s.ordinal,comment:reviews[s.slide].comment}}));const payload={{schema:responseSchema,surface,status:'user-confirmed',svg_roster_sha256:rosterHash,changes}};$('result-json').value=JSON.stringify(payload,null,2);$('copy-area').style.display='block';$('copy-area').scrollIntoView({{behavior:'smooth',block:'end'}})}}catch(e){{status.textContent=e.message;status.className='error'}}}};
$('copy').onclick=async()=>{{const text=$('result-json').value;try{{await navigator.clipboard.writeText(text);$('copy').textContent='已复制'}}catch(e){{$('result-json').focus();$('result-json').select();document.execCommand('copy');$('copy').textContent='已复制'}}}};
render();
</script>
</body></html>'''


def build(project: Path) -> dict[str, Any]:
    project = project.resolve()
    files = _slide_files(project)
    roster, roster_hash = _roster(files)
    slides = []
    for row, path in zip(roster, files):
        slides.append({**row, "svg": _sanitized_svg(path)})
    runtime = project / "live_preview"
    runtime.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "surface": SURFACE,
        "svg_roster_sha256": roster_hash,
        "slide_count": len(slides),
        "slides": roster,
    }
    manifest_path = runtime / "deck_review_manifest.json"
    html_path = runtime / "deck_review.html"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(_page_html(slides, roster_hash), encoding="utf-8")
    return {
        "schema": "ppt-master-static-deck-review-handoff/v1",
        "surface": SURFACE,
        "status": "ready",
        "svg_roster_sha256": roster_hash,
        "slide_count": len(slides),
        "launch_path": str(html_path),
        "manifest_path": str(manifest_path),
        "feedback_mode": "copy-json",
    }


def _read_response(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid review JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("review response must be a JSON object")
    return value


def apply_response(project: Path, response: dict[str, Any]) -> dict[str, Any]:
    project = project.resolve()
    runtime = project / "live_preview"
    manifest_path = runtime / "deck_review_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"deck review manifest missing: {manifest_path}; run build first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if response.get("schema") != RESPONSE_SCHEMA:
        raise RuntimeError("unsupported deck review response schema")
    if response.get("surface") != SURFACE or response.get("status") != "user-confirmed":
        raise RuntimeError("deck review response is not an explicit user confirmation")
    expected = str(manifest.get("svg_roster_sha256") or "")
    if response.get("svg_roster_sha256") != expected:
        raise RuntimeError("deck review SVG roster hash mismatch; rebuild review after slide changes")
    roster = {row["slide"]: row for row in manifest.get("slides") or []}
    changes = response.get("changes")
    if not isinstance(changes, list):
        raise RuntimeError("changes must be an array")
    seen = set()
    normalized = []
    for item in changes:
        if not isinstance(item, dict):
            raise RuntimeError("each change must be an object")
        slide = str(item.get("slide") or "")
        comment = str(item.get("comment") or "").strip()
        if slide not in roster:
            raise RuntimeError(f"review references unknown slide: {slide}")
        if slide in seen:
            raise RuntimeError(f"duplicate review change: {slide}")
        if not comment:
            raise RuntimeError(f"review change requires comment: {slide}")
        seen.add(slide)
        normalized.append({"slide": slide, "ordinal": roster[slide]["ordinal"], "comment": comment})
    persisted = {**response, "changes": normalized}
    response_path = runtime / "deck_review_response.json"
    receipt_path = runtime / "deck_review_receipt.json"
    response_path.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "surface": SURFACE,
        "status": "validated-and-persisted-by-pinned-harness",
        "svg_roster_sha256": expected,
        "slide_count": int(manifest.get("slide_count") or len(roster)),
        "changes_count": len(normalized),
        "result": "approved" if not normalized else "changes-requested",
        "response_path": str(response_path),
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PPT Master framework-free Deck Review handoff")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("project")
    a = sub.add_parser("apply-response")
    a.add_argument("project")
    a.add_argument("--response-file")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build(Path(args.project))
        else:
            result = apply_response(Path(args.project), _read_response(args.response_file))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"deck_review_handoff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
