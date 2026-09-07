#!/usr/bin/env python3
"""Framework-free per-slide Deck Review handoff for PPT Master Studio.

Builds a self-contained HTML review surface from the project's real SVG files.
The user reviews every page, marks it approved or requests changes, and copies
one JSON response back to the host. No Flask server or local HTTP listener is
required.

A rebuild may highlight which slides changed since the preceding review, but
prior decisions are evidence only: every new SVG roster still requires a new
user response and a new pinned-Harness receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from console_encoding import configure_utf8_stdio  # noqa: E402
from review_io import write_text_atomic  # noqa: E402
from review_snapshot import snapshot_svg  # noqa: E402
from slide_roster import discover_slide_svgs  # noqa: E402

RESPONSE_SCHEMA = "ppt-master-static-deck-review-response/v1"
MANIFEST_SCHEMA = "ppt-master-static-deck-review-manifest/v1"
RECEIPT_SCHEMA = "ppt-master-static-deck-review-receipt/v1"
SURFACE = "deck-review"


def _slide_files(project: Path) -> list[Path]:
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        raise RuntimeError(f"svg_output missing: {svg_dir}")
    files = [path for path in discover_slide_svgs(svg_dir) if path.is_file()]
    if not files:
        raise RuntimeError(f"no SVG slides found: {svg_dir}")
    return files


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_roster(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _sha256_bytes(canonical)


def _snapshot(files: list[Path]) -> tuple[list[dict[str, Any]], str, list[str]]:
    rows, previews = [], []
    for index, path in enumerate(files, start=1):
        raw_hash, preview, resources = snapshot_svg(path)
        row = {"slide": path.name, "ordinal": index, "sha256": raw_hash}
        # Additive dependency binding; resource-free legacy rosters keep their hash.
        if resources:
            row["resources"] = resources
        rows.append(row)
        previews.append(preview)
    return rows, _hash_roster(rows), previews


def _roster(files: list[Path]) -> tuple[list[dict[str, Any]], str]:
    rows, roster_hash, _ = _snapshot(files)
    return rows, roster_hash


def _manifest_roster(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("surface") != SURFACE:
        raise RuntimeError("unsupported review manifest; rebuild review")
    rows = manifest.get("slides")
    if not isinstance(rows, list) or not rows or type(manifest.get("slide_count")) is not int:
        raise RuntimeError("invalid review manifest roster; rebuild review")
    if manifest["slide_count"] != len(rows):
        raise RuntimeError("review manifest slide count mismatch; rebuild review")
    canonical, seen = [], set()
    for ordinal, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise RuntimeError("invalid review manifest row")
        name = row.get("slide")
        if not isinstance(name, str) or Path(name).name != name or name in seen:
            raise RuntimeError("duplicate or invalid review slide")
        if type(row.get("ordinal")) is not int or row["ordinal"] != ordinal:
            raise RuntimeError("invalid review slide ordinal")
        if not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise RuntimeError("invalid review slide digest")
        item = {key: row[key] for key in ("slide", "ordinal", "sha256")}
        if "resources" in row:
            resources = row["resources"]
            if not isinstance(resources, list) or not resources:
                raise RuntimeError("invalid review resource roster")
            for resource in resources:
                if (not isinstance(resource, dict) or not isinstance(resource.get("path"), str)
                        or not isinstance(resource.get("sha256"), str)
                        or not re.fullmatch(r"[0-9a-f]{64}", resource["sha256"])):
                    raise RuntimeError("invalid review resource digest")
            item["resources"] = resources
        canonical.append(item)
        seen.add(name)
    if manifest.get("svg_roster_sha256") != _hash_roster(canonical):
        raise RuntimeError("review manifest roster hash mismatch; rebuild review")
    return canonical


def _validate_response(manifest: dict[str, Any], response: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _manifest_roster(manifest)
    if not isinstance(response, dict) or response.get("schema") != RESPONSE_SCHEMA:
        raise RuntimeError("unsupported deck review response schema")
    if response.get("surface") != SURFACE or response.get("status") != "user-confirmed":
        raise RuntimeError("review response is not explicit user confirmation")
    if response.get("svg_roster_sha256") != manifest["svg_roster_sha256"]:
        raise RuntimeError("deck review SVG roster hash mismatch; rebuild review after slide changes")
    roster = {row["slide"]: row for row in rows}
    changes = response.get("changes")
    if not isinstance(changes, list):
        raise RuntimeError("changes must be an array")
    seen = set()
    for item in changes:
        if not isinstance(item, dict) or not isinstance(item.get("slide"), str):
            raise RuntimeError("each review change must identify a slide")
        slide, comment = item["slide"], item.get("comment")
        if slide not in roster or slide in seen:
            raise RuntimeError("unknown or duplicate review change")
        if not isinstance(comment, str) or not comment.strip():
            raise RuntimeError("review change requires a non-empty string comment")
        if "ordinal" in item and (type(item["ordinal"]) is not int or item["ordinal"] != roster[slide]["ordinal"]):
            raise RuntimeError("review change ordinal does not match its slide")
        seen.add(slide)
    return changes


def _receipt_matches(manifest: dict[str, Any], response: dict[str, Any] | None,
                     receipt: dict[str, Any] | None) -> bool:
    if not response or not receipt:
        return False
    try:
        changes = _validate_response(manifest, response)
    except (RuntimeError, TypeError, ValueError):
        return False
    return (receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("surface") == SURFACE
            and receipt.get("status") == "validated-and-persisted-by-pinned-harness"
            and receipt.get("svg_roster_sha256") == manifest["svg_roster_sha256"]
            and type(receipt.get("slide_count")) is int and receipt["slide_count"] == manifest["slide_count"]
            and type(receipt.get("changes_count")) is int and receipt["changes_count"] == len(changes)
            and receipt.get("result") == ("changes-requested" if changes else "approved")
            and ("reviewed_slide_count" not in receipt or
                 (type(receipt["reviewed_slide_count"]) is int and receipt["reviewed_slide_count"] == manifest["slide_count"]))
            and ("response_sha256" not in receipt or receipt["response_sha256"] == _response_hash(response)))


def _response_hash(response: dict[str, Any]) -> str:
    return _sha256_bytes(json.dumps(response, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8"))


def _check_current(project: Path, manifest: dict[str, Any]) -> None:
    _manifest_roster(manifest)
    _, live_hash = _roster(_slide_files(project))
    if live_hash != manifest["svg_roster_sha256"]:
        raise RuntimeError("live SVG/resource roster hash mismatch; rebuild review")
    html = project / "live_preview/deck_review.html"
    if not html.is_file() or (manifest.get("html_sha256") and
                            manifest["html_sha256"] != _sha256_bytes(html.read_bytes())):
        raise RuntimeError("review HTML missing or changed; rebuild review")


def review_status(project: Path) -> dict[str, Any]:
    """Project the owning Gate evidence without issuing a new approval."""
    project = project.resolve()
    runtime = project / "live_preview"
    manifest = _load_object(runtime / "deck_review_manifest.json")
    if not manifest:
        return {"generated": False, "launch_ready": False, "validated": False, "applied": False,
                "user_submitted": False, "stale": (runtime / "deck_review_manifest.json").exists(),
                "next_action": "build-deck-review-after-final-svg-quality-pass"}
    try:
        _check_current(project, manifest)
    except (RuntimeError, OSError, ValueError) as exc:
        return {"generated": True, "launch_ready": False, "validated": False, "applied": False,
                "user_submitted": False, "stale": True, "next_action": "rebuild-deck-review",
                "error": str(exc)}
    response = _load_object(runtime / "deck_review_response.json")
    receipt = _load_object(runtime / "deck_review_receipt.json")
    accepted = _receipt_matches(manifest, response, receipt)
    result = receipt.get("result") if accepted else None
    return {"generated": True, "launch_ready": True, "validated": accepted, "applied": accepted,
            "user_submitted": accepted, "stale": bool(receipt and not accepted),
            "svg_roster_sha256": manifest["svg_roster_sha256"], "slide_count": manifest["slide_count"],
            "receipt_result": result,
            "next_action": ("continue-to-export" if result == "approved" else
                            "apply-requested-changes-and-rebuild-review" if result == "changes-requested" else
                            "present-review-html-and-apply-user-response")}


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _review_delta(runtime: Path, roster: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    previous_manifest = _load_object(runtime / "deck_review_manifest.json")
    if not previous_manifest:
        return [{**row, "review_delta": "new", "previous_decision": None} for row in roster], None

    try:
        _manifest_roster(previous_manifest)
    except (RuntimeError, TypeError, ValueError):
        return [{**row, "review_delta": "new", "previous_decision": None} for row in roster], None
    previous_hash = str(previous_manifest.get("svg_roster_sha256") or "")
    old_rows = {
        str(row.get("slide") or ""): row
        for row in previous_manifest.get("slides") or []
        if isinstance(row, dict) and row.get("slide")
    }
    receipt = _load_object(runtime / "deck_review_receipt.json")
    response = _load_object(runtime / "deck_review_response.json")
    receipt_valid = _receipt_matches(previous_manifest, response, receipt)
    response_valid = receipt_valid
    change_comments: dict[str, str] = {}
    if receipt_valid and response_valid:
        for item in response.get("changes") or []:
            if isinstance(item, dict) and item.get("slide"):
                change_comments[str(item["slide"])] = str(item.get("comment") or "")

    enhanced: list[dict[str, Any]] = []
    changed_count = 0
    for row in roster:
        old = old_rows.get(row["slide"])
        if old is None:
            delta = "added"
        elif (str(old.get("sha256") or "") == row["sha256"]
              and old.get("resources", []) == row.get("resources", [])
              and old.get("ordinal") == row["ordinal"]):
            delta = "unchanged"
        else:
            delta = "changed"
        if delta != "unchanged":
            changed_count += 1
        previous_decision = None
        previous_comment = ""
        if receipt_valid and old is not None:
            if row["slide"] in change_comments:
                previous_decision = "changes"
                previous_comment = change_comments[row["slide"]]
            else:
                previous_decision = "approved"
        enhanced.append(
            {
                **row,
                "review_delta": delta,
                "previous_decision": previous_decision,
                "previous_comment": previous_comment,
            }
        )

    current_names = {row["slide"] for row in roster}
    removed = sorted(name for name in old_rows if name not in current_names)
    summary = {
        "available": True,
        "svg_roster_sha256": previous_hash,
        "receipt_valid": receipt_valid,
        "receipt_result": receipt.get("result") if receipt_valid and receipt else None,
        "changed_slide_count": changed_count,
        "removed_slides": removed,
        "approval_reuse_allowed": False,
    }
    return enhanced, summary


def _sanitized_svg(path: Path) -> str:
    return snapshot_svg(path)[1]


def _page_html(slides: list[dict[str, Any]], roster_hash: str, previous_review: dict[str, Any] | None) -> str:
    slide_json = json.dumps(slides, ensure_ascii=False).replace("<", "\\u003c")
    roster_json = json.dumps(roster_hash)
    schema_json = json.dumps(RESPONSE_SCHEMA)
    surface_json = json.dumps(SURFACE)
    previous_json = json.dumps(previous_review, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PPT Master Studio · Deck Review</title>
<style>
:root{{--bg:#0b1020;--panel:#121a2b;--line:#2c3950;--text:#d7e2f0;--muted:#8fa1b8;--blue:#5ea8ff;--amber:#ffb84d;--green:#5dd6c0;--red:#ff7a7a}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,"Noto Sans CJK SC",system-ui,sans-serif}}
#app{{height:100vh;display:grid;grid-template-columns:250px minmax(0,1fr) 340px}}
.panel{{background:var(--panel);border-color:var(--line)}} #left{{border-right:1px solid var(--line);overflow:auto}} #right{{border-left:1px solid var(--line);padding:18px;overflow:auto}}
.header{{padding:16px 18px;border-bottom:1px solid var(--line);font-weight:700}} #progress,#delta-summary{{font-size:12px;color:var(--muted);margin-top:4px}}
#list{{padding:10px}} .slide-btn{{width:100%;display:flex;gap:8px;align-items:center;text-align:left;padding:9px 10px;margin:4px 0;border:1px solid transparent;border-radius:8px;background:transparent;color:var(--text);cursor:pointer}}
.slide-btn:hover,.slide-btn.active{{background:#18243a;border-color:#32445f}} .dot{{width:9px;height:9px;border-radius:50%;background:#506079;flex:0 0 auto}} .approved .dot{{background:var(--green)}} .changes .dot{{background:var(--amber)}} .delta{{font-size:10px;padding:2px 5px;border-radius:999px;border:1px solid #5e4b27;color:var(--amber);margin-left:auto}} .delta.unchanged{{border-color:#33445c;color:var(--muted)}}
#center{{min-width:0;display:flex;flex-direction:column}} #nav{{height:56px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:center;gap:14px}} #nav button,#actions button,#copy-area button{{border:1px solid #425673;background:#18243a;color:var(--text);border-radius:8px;padding:8px 12px;cursor:pointer}}
#nav button:disabled,#actions button:disabled{{opacity:.4;cursor:not-allowed}} #slide-name{{min-width:180px;text-align:center;color:var(--muted)}}
#canvas-wrap{{flex:1;min-height:0;padding:24px;display:flex;align-items:center;justify-content:center;overflow:auto}} #canvas{{width:min(100%,1280px);aspect-ratio:16/9;background:#fff;box-shadow:0 14px 50px rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;overflow:hidden}}
.review-title{{font-size:18px;font-weight:750;margin:0 0 8px}} .review-note{{color:var(--muted);font-size:12px;margin-bottom:18px}} .history{{border:1px solid var(--line);border-radius:8px;padding:9px 10px;margin:0 0 14px;font-size:12px;color:var(--muted)}} .history.changed{{border-color:#725b30;color:var(--amber)}} .choice{{display:block;border:1px solid var(--line);border-radius:9px;padding:12px;margin:10px 0;cursor:pointer}} .choice input{{margin-right:8px}}
textarea{{width:100%;min-height:130px;resize:vertical;border:1px solid #425673;border-radius:8px;background:#0d1525;color:var(--text);padding:10px;font:inherit}} #actions{{display:grid;gap:9px;margin-top:14px}} #save-next{{background:#1f5f97!important;border-color:var(--blue)!important}} #complete{{background:#235d50!important;border-color:var(--green)!important;font-weight:700}}
#copy-area{{display:none;margin-top:18px;padding-top:16px;border-top:1px solid var(--line)}} #result-json{{min-height:210px;font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}} .error{{color:var(--red)}} .ok{{color:var(--green)}}
@media(max-width:1000px){{#app{{height:auto;display:flex;flex-direction:column}}#left{{max-height:180px}}#center{{min-height:340px}}#right{{border-left:0}}#canvas-wrap{{padding:12px}}#slide-name{{min-width:0;overflow-wrap:anywhere}}}}
</style>
</head>
<body>
<div id="app">
  <section id="left" class="panel"><div class="header">逐页 Review<div id="progress"></div><div id="delta-summary"></div></div><div id="list"></div></section>
  <main id="center"><div id="nav"><button id="prev">‹ 上一页</button><span id="slide-name"></span><button id="next">下一页 ›</button></div><div id="canvas-wrap"><div id="canvas"></div></div></main>
  <aside id="right" class="panel">
    <h2 class="review-title">本页结论</h2>
    <div class="review-note">这里渲染的是当前真实 SVG，不是截图。即使页面与上次一致，新的 roster 仍要求逐页明确决定；历史信息只用于定位变化，不会自动复用批准。</div>
    <div id="history" class="history"></div>
    <label class="choice"><input type="radio" name="decision" value="approved">通过</label>
    <label class="choice"><input type="radio" name="decision" value="changes">需要修改</label>
    <textarea id="comment" placeholder="例如：P07 右侧因果链太密，保留结论但把日志证据拆成上下两层。"></textarea>
    <div id="status"></div>
    <div id="actions"><button id="save-next">保存本页并到下一页</button><button id="complete" disabled>完成逐页 Review</button></div>
    <div id="copy-area"><h3>Review JSON 已生成</h3><div class="review-note">复制下面 JSON 原样粘贴回 ChatGPT。页面不会自动关闭。</div><textarea id="result-json" readonly></textarea><button id="copy">复制 Review JSON</button></div>
  </aside>
</div>
<script>
const slides={slide_json}; const rosterHash={roster_json}; const responseSchema={schema_json}; const surface={surface_json}; const previousReview={previous_json};
let index=0; const reviews={{}};
const $=id=>document.getElementById(id); const list=$('list'), canvas=$('canvas'), status=$('status'), comment=$('comment');
function valid(r){{return r && (r.decision==='approved' || (r.decision==='changes' && r.comment.trim()))}}
function reviewedCount(){{return slides.filter(s=>valid(reviews[s.slide])).length}}
let revision=0;
function invalidateResponse(){{revision++;$('result-json').value='';$('copy-area').style.display='none';$('copy').textContent='复制 Review JSON';}}
function esc(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function deltaLabel(s){{return s.review_delta==='unchanged'?'未变化':s.review_delta==='changed'?'已变化':s.review_delta==='added'?'新增':'首次'}}
function renderList(){{list.innerHTML='';slides.forEach((s,i)=>{{const b=document.createElement('button');b.className='slide-btn '+(i===index?'active ':'')+(reviews[s.slide]?.decision||'');b.innerHTML=`<span class="dot"></span><span>${{String(s.ordinal).padStart(2,'0')}} · ${{esc(s.slide)}}</span><span class="delta ${{s.review_delta}}">${{deltaLabel(s)}}</span>`;b.onclick=()=>{{saveDraft();index=i;render()}};list.appendChild(b)}})}}
function loadReview(){{const s=slides[index],r=reviews[s.slide]||{{}};document.querySelectorAll('input[name=decision]').forEach(x=>x.checked=x.value===r.decision);comment.value=r.comment||'';comment.disabled=r.decision!=='changes';}}
function saveDraft(strict=false){{const s=slides[index];const selected=document.querySelector('input[name=decision]:checked');const decision=selected?.value||'';const text=decision==='changes'?comment.value.trim():'';const next={{decision,comment:text}};if(JSON.stringify(reviews[s.slide])!==JSON.stringify(next)){{reviews[s.slide]=next;invalidateResponse()}}if(strict&&!valid(next))throw new Error(decision==='changes'?'选择“需要修改”时必须填写修改意见':'请先选择“通过”或“需要修改”');}}

function historyText(s){{let text=`与上一次 Review：${{deltaLabel(s)}}。`;if(s.previous_decision==='approved')text+=' 上次决定：通过。';if(s.previous_decision==='changes')text+=` 上次决定：需要修改${{s.previous_comment?'（'+s.previous_comment+'）':''}}。`;if(!s.previous_decision&&previousReview)text+=' 没有可复用的有效历史决定。';return text}}
function render(){{const s=slides[index];$('complete').textContent=`完成 ${{slides.length}} 页 Review`;$('slide-name').textContent=`${{s.ordinal}} / ${{slides.length}} · ${{s.slide}}`;$('prev').disabled=index===0;$('next').disabled=index===slides.length-1;canvas.innerHTML=s.svg;const actual=canvas.querySelector('svg');if(!actual)throw new Error('SVG 无法显示，不能审阅');const vb=actual.viewBox.baseVal;if(vb.width>0&&vb.height>0)canvas.style.aspectRatio=vb.width+'/'+vb.height;loadReview();renderList();$('progress').textContent=`已确认 ${{reviewedCount()}} / ${{slides.length}}`;$('delta-summary').textContent=previousReview?`自上次 Review 起变化 ${{previousReview.changed_slide_count}} 页${{previousReview.removed_slides?.length?'，移除 '+previousReview.removed_slides.length+' 页':''}}`:'首次 Review';$('complete').disabled=reviewedCount()!==slides.length;status.textContent='';$('history').textContent=historyText(s);$('history').className='history '+(s.review_delta==='unchanged'?'':'changed');}}
document.querySelectorAll('input[name=decision]').forEach(x=>x.onchange=()=>{{comment.disabled=x.value!=='changes';if(x.value==='approved')comment.value='';invalidateResponse();saveDraft();renderList();$('complete').disabled=reviewedCount()!==slides.length;}});
comment.oninput=()=>{{invalidateResponse();saveDraft();renderList();$('complete').disabled=reviewedCount()!==slides.length;}};
$('prev').onclick=()=>{{saveDraft();if(index>0){{index--;render()}}}};$('next').onclick=()=>{{saveDraft();if(index<slides.length-1){{index++;render()}}}};
$('save-next').onclick=()=>{{try{{saveDraft(true);render();if(index<slides.length-1){{index++;render()}}status.textContent='本页已记录';status.className='ok'}}catch(e){{status.textContent=e.message;status.className='error'}}}};
$('complete').onclick=()=>{{try{{invalidateResponse();saveDraft(true);if(reviewedCount()!==slides.length)throw new Error('仍有页面没有确认');const changes=slides.filter(s=>reviews[s.slide].decision==='changes').map(s=>({{slide:s.slide,ordinal:s.ordinal,comment:reviews[s.slide].comment}}));const payload={{schema:responseSchema,surface,status:'user-confirmed',svg_roster_sha256:rosterHash,changes}};$('result-json').value=JSON.stringify(payload,null,2);$('copy-area').style.display='block';$('copy-area').scrollIntoView({{behavior:'smooth',block:'end'}})}}catch(e){{status.textContent=e.message;status.className='error'}}}};
$('copy').onclick=async()=>{{const text=$('result-json').value;const version=revision;if(!text)return;let copied=false;try{{await navigator.clipboard.writeText(text);copied=true}}catch(e){{try{{$('result-json').focus();$('result-json').select();copied=document.execCommand('copy')===true}}catch(f){{copied=false}}}}if(version===revision)$('copy').textContent=copied?'已复制':'自动复制失败，请手动复制';}};
render();
</script>
</body></html>'''


def build(project: Path) -> dict[str, Any]:
    project = project.resolve()
    files = _slide_files(project)
    roster, roster_hash, previews = _snapshot(files)
    runtime = project / "live_preview"
    runtime.mkdir(parents=True, exist_ok=True)
    enhanced_roster, previous_review = _review_delta(runtime, roster)
    slides = []
    for row, preview in zip(enhanced_roster, previews):
        slides.append({**row, "svg": preview})
    changed_count = sum(1 for row in enhanced_roster if row.get("review_delta") != "unchanged")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "surface": SURFACE,
        "svg_roster_sha256": roster_hash,
        "slide_count": len(slides),
        "changed_slide_count": changed_count,
        "previous_review": previous_review,
        "slides": enhanced_roster,
    }
    manifest_path = runtime / "deck_review_manifest.json"
    html_path = runtime / "deck_review.html"
    page = _page_html(slides, roster_hash, previous_review)
    manifest["html_sha256"] = _sha256_bytes(page.encode("utf-8"))
    manifest["hash_scope"] = "svg-and-prepared-resources/v1"
    write_text_atomic(html_path, page)
    write_text_atomic(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {
        "schema": "ppt-master-static-deck-review-handoff/v1",
        "surface": SURFACE,
        "status": "ready",
        "svg_roster_sha256": roster_hash,
        "slide_count": len(slides),
        "changed_slide_count": changed_count,
        "previous_review": previous_review,
        "launch_path": str(html_path),
        "manifest_path": str(manifest_path),
        "feedback_mode": "copy-json",
        "interaction_state": {
            "generated": True,
            "launch_ready": True,
            "access_provided": None,
            "user_submitted": False,
            "validated": False,
            "applied": False,
            "stale": False,
            "next_action": "present-review-html-and-apply-user-response",
        },
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
    changes = _validate_response(manifest, response)
    _check_current(project, manifest)
    expected = manifest["svg_roster_sha256"]
    roster = _manifest_roster(manifest)
    response_path = runtime / "deck_review_response.json"
    receipt_path = runtime / "deck_review_receipt.json"
    # Preserve the submitted JSON object, including literal comments and ordinals.
    write_text_atomic(response_path, json.dumps(response, ensure_ascii=False, indent=2) + "\n")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "surface": SURFACE,
        "status": "validated-and-persisted-by-pinned-harness",
        "svg_roster_sha256": expected,
        "slide_count": int(manifest.get("slide_count") or len(roster)),
        "reviewed_slide_count": len(roster),
        "changes_count": len(changes),
        "result": "approved" if not changes else "changes-requested",
        "response_path": str(response_path),
        "response_sha256": _response_hash(response),
        "interaction_state": {
            "generated": True,
            "launch_ready": True,
            "access_provided": None,
            "user_submitted": True,
            "validated": True,
            "applied": True,
            "stale": False,
            "next_action": "continue-to-export" if not changes else "apply-requested-changes-and-rebuild-review",
        },
    }
    _check_current(project, manifest)
    write_text_atomic(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="PPT Master framework-free Deck Review handoff")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("project")
    a = sub.add_parser("apply-response")
    a.add_argument("project")
    a.add_argument("--response-file")
    for name in ("status", "assert-approved"):
        check = sub.add_parser(name)
        check.add_argument("project")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build(Path(args.project))
        elif args.command in {"status", "assert-approved"}:
            result = review_status(Path(args.project))
            if args.command == "assert-approved" and not (result["validated"] and result.get("receipt_result") == "approved"):
                raise RuntimeError("current Deck Review is not approved; complete the owning human review gate")
        else:
            result = apply_response(Path(args.project), _read_response(args.response_file))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"deck_review_handoff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
