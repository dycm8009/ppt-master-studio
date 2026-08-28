#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "ppt-master"
CONFIRM_DOC_DIR = SKILL_DIR / "scripts" / "confirm_ui"
CATALOGS_PATH = CONFIRM_DOC_DIR / "static" / "catalogs.json"
TEMPLATES_DIR = SKILL_DIR / "templates"

RESPONSE_SCHEMA = "ppt-master-studio-stage1-mini-app-response/v1"
PROSE_FIELDS = (
    "audience",
    "communication_intent",
    "audience_outcome",
    "core_message",
    "delivery_context",
    "artifact_afterlife",
    "content_divergence",
)
TEMPLATE_LIBRARY_CONFIG = {
    "brand": ("brands", "brands_index.json"),
    "style": ("styles", "styles_index.json"),
    "layout": ("layouts", "layouts_index.json"),
    "deck": ("decks", "decks_index.json"),
}


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _canonical_sha(data: object) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ui_lang(value: object) -> str:
    raw = str(value or "zh").strip().lower()
    if raw.startswith("zh-tw") or raw.startswith("zh-hant"):
        return "zh_tw"
    if raw.startswith("en"):
        return "en"
    if raw.startswith("ja"):
        return "ja"
    return "zh"


def _localized(entry: dict, base: str, lang: str, fallback: str = "") -> str:
    for key in (f"{base}_{lang}", base, f"{base}_zh", f"{base}_en", f"{base}_ja", f"{base}_zh_tw"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _load_canvas_catalog(lang: str) -> list[dict]:
    catalogs = _read_json(CATALOGS_PATH)
    canvas = catalogs.get("canvas")
    if not isinstance(canvas, list) or not canvas:
        raise ValueError("official catalogs.json canvas list is missing")
    result = []
    for item in canvas:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("official canvas catalog contains an invalid entry")
        cid = item["id"]
        result.append({
            "id": cid,
            "label": _localized(item, "label", lang, cid),
            "use": _localized(item, "use", lang, ""),
        })
    return result


def _load_library() -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for kind, (directory_name, index_name) in TEMPLATE_LIBRARY_CONFIG.items():
        kind_dir = (TEMPLATES_DIR / directory_name).resolve()
        index = _read_json(kind_dir / index_name)
        group = []
        for template_id, metadata in index.items():
            if not isinstance(template_id, str) or re.fullmatch(r"\w[\w.-]*", template_id) is None:
                raise ValueError(f"unsafe template id in {index_name}: {template_id!r}")
            if not isinstance(metadata, dict):
                raise ValueError(f"invalid metadata for {kind}:{template_id}")
            root = (kind_dir / template_id).resolve()
            group.append({
                "id": template_id,
                "label": str(metadata.get("label") or template_id),
                "summary": str(metadata.get("summary") or ""),
                "workspace_root": str(root),
            })
        groups[kind] = group
    return groups


def _load_stage1(project: Path) -> dict:
    confirm_dir = project / "confirm_ui"
    recommendation = _read_json(confirm_dir / "recommendations.stage1.json")
    options = _read_json(confirm_dir / "template_options.json")

    if recommendation.get("stage") != "stage1":
        raise ValueError("recommendations.stage1.json must declare stage=stage1")
    primary_language = recommendation.get("primary_language")
    if not isinstance(primary_language, str) or not primary_language.strip():
        raise ValueError("Stage 1 primary_language is required")
    recommend = recommendation.get("recommend")
    if not isinstance(recommend, dict) or not isinstance(recommend.get("canvas"), str):
        raise ValueError("Stage 1 recommend.canvas is required")

    prose = {}
    for name in PROSE_FIELDS:
        item = recommendation.get(name)
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            raise ValueError(f"Stage 1 {name}.value must be a string")
        prose[name] = {
            "value": item["value"],
            "locked": item.get("locked") is True,
        }

    if options.get("schema_version") != 1 or options.get("phase") != "template":
        raise ValueError("template_options.json must use schema_version=1 and phase=template")
    default_mode = options.get("default_mode")
    if default_mode not in {"free_design", "templates"}:
        raise ValueError("template_options.json default_mode is invalid")
    explicit_roots = options.get("explicit_workspace_roots")
    if not isinstance(explicit_roots, list) or not all(isinstance(v, str) and v.strip() for v in explicit_roots):
        raise ValueError("template_options.json explicit_workspace_roots must be a string array")

    lang = _ui_lang(recommendation.get("lang") or options.get("lang"))
    canvases = _load_canvas_catalog(lang)
    canvas_ids = {item["id"] for item in canvases}
    if recommend["canvas"] not in canvas_ids:
        raise ValueError(f"recommended canvas is not in the official catalog: {recommend['canvas']}")

    library = _load_library()
    registered_by_root = {
        item["workspace_root"]: (kind, item["id"])
        for kind, items in library.items()
        for item in items
    }
    canonical_explicit = []
    preselected_library = {kind: "" for kind in TEMPLATE_LIBRARY_CONFIG}
    preselected_root = ""
    for raw in explicit_roots:
        root = str(Path(raw).resolve())
        canonical_explicit.append(root)
    if len(canonical_explicit) == 1:
        root = canonical_explicit[0]
        registered = registered_by_root.get(root)
        if registered:
            preselected_library[registered[0]] = registered[1]
        else:
            preselected_root = root

    context = {
        "surface": "stage1",
        "lang": lang,
        "primary_language": primary_language.strip(),
        "canvas": recommend["canvas"],
        "canvases": canvases,
        "prose": prose,
        "template": {
            "default_mode": default_mode,
            "library": library,
            "explicit_workspace_roots": canonical_explicit,
            "preselected_library": preselected_library,
            "preselected_root": preselected_root,
        },
    }
    context["context_sha256"] = _canonical_sha(context)
    return context


def _safe_json_for_script(data: object) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render(project: Path) -> str:
    ctx = _load_stage1(project.resolve())
    payload = _safe_json_for_script(ctx)
    prose_labels = {
        "audience": "受众 / Audience",
        "communication_intent": "沟通意图 / Communication intent",
        "audience_outcome": "期望受众结果 / Audience outcome",
        "core_message": "核心信息 / Core message",
        "delivery_context": "交付场景 / Delivery context",
        "artifact_afterlife": "材料后续用途 / Artifact afterlife",
        "content_divergence": "内容重构边界 / Content divergence",
    }
    labels = _safe_json_for_script(prose_labels)

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PPT Master Studio · Stage 1</title>
<style>
:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
*{{box-sizing:border-box}} body{{margin:0;background:#0b0b0c;color:#f5f5f5;padding:22px}}
.app{{max-width:900px;margin:0 auto}} .badge{{display:inline-block;border:1px solid #343438;border-radius:999px;padding:6px 10px;font-size:12px;color:#c8c8cc;margin-bottom:14px}}
h1{{font-size:25px;margin:0 0 7px}} .sub{{color:#aaaab0;line-height:1.55;margin:0 0 20px}} .panel{{background:#1c1c1f;border:1px solid #343438;border-radius:18px;padding:20px;margin:0 0 14px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} @media(max-width:680px){{.grid{{grid-template-columns:1fr}}}}
.field{{margin-bottom:15px}} label{{display:block;color:#d6d6da;font-size:13px;font-weight:650;margin-bottom:7px}}
input,select,textarea{{width:100%;background:#121214;color:#fff;border:1px solid #3b3b40;border-radius:11px;padding:11px 12px;font:inherit;outline:none}}
textarea{{min-height:84px;resize:vertical}} input:focus,select:focus,textarea:focus{{border-color:#e66c63;box-shadow:0 0 0 3px rgba(230,108,99,.12)}}
textarea[readonly]{{opacity:.68}} .hint{{font-size:12px;color:#898990;margin-top:6px;line-height:1.4}} .templates{{display:none}} .templates.on{{display:block}}
.actions{{display:flex;gap:10px;flex-wrap:wrap}} button{{border:0;border-radius:11px;padding:11px 16px;font:inherit;cursor:pointer}} #confirm{{background:#e66c63;color:#111;font-weight:750}} #copy{{background:#303034;color:#fff}} #copy:disabled{{opacity:.45;cursor:not-allowed}}
.result{{display:none;margin-top:16px}} .result.on{{display:block}} #out{{min-height:210px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}} .status{{margin-top:8px;color:#9fdfa8;font-size:12px}} .error{{color:#ff8d85}}
</style></head>
<body><div class="app">
<div class="badge">PPT Master Studio · Stage 1 mini app</div>
<h1>确认沟通契约与模板选择</h1>
<p class="sub">数据来自当前 pinned PPT Master 官方 Stage 1。此 mini app 只是 ChatGPT 确认载体；不会创建或伪造 Confirm UI receipt。</p>
<div class="panel"><div class="grid">
<div class="field"><label>内容语言 / Primary language</label><input id="primary_language"></div>
<div class="field"><label>画布 / Canvas</label><select id="canvas"></select></div>
</div><div id="prose"></div></div>
<div class="panel"><div class="field"><label>设计来源 / Design source</label><select id="template_mode"><option value="free_design">Free design</option><option value="templates">Use templates</option></select></div>
<div id="templates" class="templates"><div class="grid" id="library"></div><div class="field"><label>指定模板工作区 / Specified workspace</label><select id="specified"><option value="">None</option></select><div class="hint">模板组合的最终合法性仍由官方 Harness 在聊天分支验证。</div></div></div></div>
<div class="panel"><div class="actions"><button id="confirm">确认当前 Stage 1</button><button id="copy" disabled>复制确认 JSON</button></div><div id="result" class="result"><textarea id="out" readonly></textarea><div id="status" class="status"></div></div></div>
</div>
<script>
const CTX={payload}; const LABELS={labels}; const KINDS=['brand','style','layout','deck'];
const $=id=>document.getElementById(id);
$('primary_language').value=CTX.primary_language;
CTX.canvases.forEach(c=>{{const o=document.createElement('option');o.value=c.id;o.textContent=c.label+(c.use?' · '+c.use:'');if(c.id===CTX.canvas)o.selected=true;$('canvas').appendChild(o)}});
Object.entries(CTX.prose).forEach(([id,item])=>{{const box=document.createElement('div');box.className='field';const l=document.createElement('label');l.textContent=LABELS[id]||id;const t=document.createElement('textarea');t.id=id;t.value=item.value||'';if(item.locked){{t.readOnly=true;}}box.append(l,t);if(item.locked){{const h=document.createElement('div');h.className='hint';h.textContent='Locked by the active official profile';box.appendChild(h)}}$('prose').appendChild(box)}});
function addKind(kind){{const f=document.createElement('div');f.className='field';const l=document.createElement('label');l.textContent=kind[0].toUpperCase()+kind.slice(1);const s=document.createElement('select');s.id='tpl_'+kind;const none=document.createElement('option');none.value='';none.textContent='None';s.appendChild(none);(CTX.template.library[kind]||[]).forEach(x=>{{const o=document.createElement('option');o.value=x.id;o.textContent=x.label+(x.summary?' · '+x.summary:'');if(CTX.template.preselected_library[kind]===x.id)o.selected=true;s.appendChild(o)}});f.append(l,s);$('library').appendChild(f)}}
KINDS.forEach(addKind); CTX.template.explicit_workspace_roots.forEach(root=>{{const o=document.createElement('option');o.value=root;o.textContent=root;if(CTX.template.preselected_root===root)o.selected=true;$('specified').appendChild(o)}});
$('template_mode').value=CTX.template.default_mode; function syncTemplates(){{$('templates').classList.toggle('on',$('template_mode').value==='templates')}} $('template_mode').addEventListener('change',syncTemplates);syncTemplates();
function decision(){{const library={{}};KINDS.forEach(k=>library[k]=$('tpl_'+k).value||null);const mode=$('template_mode').value;return {{schema:'{RESPONSE_SCHEMA}',surface:'stage1',status:'user-confirmed',context_sha256:CTX.context_sha256,values:{{primary_language:$('primary_language').value,canvas:$('canvas').value,audience:$('audience').value,communication_intent:$('communication_intent').value,audience_outcome:$('audience_outcome').value,core_message:$('core_message').value,delivery_context:$('delivery_context').value,artifact_afterlife:$('artifact_afterlife').value,content_divergence:$('content_divergence').value,template_choice:{{mode,library,specified_workspace_root:$('specified').value||null}}}}}}}}
$('confirm').addEventListener('click',()=>{{const d=decision();if(d.values.template_choice.mode==='templates'&&!KINDS.some(k=>d.values.template_choice.library[k])&&!d.values.template_choice.specified_workspace_root){{$('status').textContent='Template mode requires at least one template selection.';$('status').className='status error';$('result').classList.add('on');return}}$('out').value=JSON.stringify(d,null,2);$('result').classList.add('on');$('copy').disabled=false;$('status').className='status';$('status').textContent='已在 mini app 内确认。请把此 JSON 返回聊天，Harness 将按官方 chat confirmation 路径继续。'}});
$('copy').addEventListener('click',async()=>{{try{{await navigator.clipboard.writeText($('out').value);$('status').textContent='确认 JSON 已复制。'}}catch(e){{$('out').focus();$('out').select();$('status').textContent='当前 Preview 禁止剪贴板访问；JSON 已选中，可手动复制。'}}}});
</script></body></html>'''


def validate_response(project: Path, response: dict) -> dict:
    ctx = _load_stage1(project.resolve())
    errors: list[str] = []
    if response.get("schema") != RESPONSE_SCHEMA:
        errors.append("response schema mismatch")
    if response.get("surface") != "stage1" or response.get("status") != "user-confirmed":
        errors.append("response must be a confirmed stage1 surface")
    if response.get("context_sha256") != ctx["context_sha256"]:
        errors.append("response context_sha256 does not match current Stage 1 inputs")
    values = response.get("values")
    if not isinstance(values, dict):
        errors.append("values must be an object")
        values = {}
    for key in ("primary_language", "canvas", *PROSE_FIELDS):
        if not isinstance(values.get(key), str):
            errors.append(f"values.{key} must be a string")
    canvas_ids = {item["id"] for item in ctx["canvases"]}
    if isinstance(values.get("canvas"), str) and values["canvas"] not in canvas_ids:
        errors.append("values.canvas is not in the current official canvas catalog")
    for key, item in ctx["prose"].items():
        if item["locked"] and values.get(key) != item["value"]:
            errors.append(f"locked field changed: {key}")

    choice = values.get("template_choice")
    if not isinstance(choice, dict):
        errors.append("values.template_choice must be an object")
    else:
        mode = choice.get("mode")
        library = choice.get("library")
        specified = choice.get("specified_workspace_root")
        if mode not in {"free_design", "templates"}:
            errors.append("template_choice.mode is invalid")
        if not isinstance(library, dict) or set(library) != set(TEMPLATE_LIBRARY_CONFIG):
            errors.append("template_choice.library must contain brand/style/layout/deck")
            library = {}
        selected = False
        for kind in TEMPLATE_LIBRARY_CONFIG:
            value = library.get(kind)
            allowed = {item["id"] for item in ctx["template"]["library"][kind]}
            if value is not None and value not in allowed:
                errors.append(f"unknown {kind} template id: {value}")
            if value:
                selected = True
        allowed_roots = set(ctx["template"]["explicit_workspace_roots"])
        if specified is not None and specified not in allowed_roots:
            errors.append("specified workspace root is not in current template options")
        if specified:
            selected = True
        if mode == "free_design" and selected:
            errors.append("free_design cannot carry template selections")
        if mode == "templates" and not selected:
            errors.append("templates mode requires at least one selection")

    return {
        "schema": "ppt-master-studio-stage1-mini-app-validation/v1",
        "status": "passed" if not errors else "failed",
        "context_sha256": ctx["context_sha256"],
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ChatGPT Stage 1 mini-app adapter for the official PPT Master confirmation contract")
    sub = ap.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("project", type=Path)
    build.add_argument("--output", type=Path)
    build.add_argument("--code-block", action="store_true")
    validate = sub.add_parser("validate")
    validate.add_argument("project", type=Path)
    validate.add_argument("response", type=Path)
    args = ap.parse_args()

    if args.cmd == "build":
        out = render(args.project)
        if args.code_block:
            out = "```html\n" + out + "\n```"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out + "\n", encoding="utf-8")
        else:
            print(out)
        return 0

    response = _read_json(args.response)
    report = validate_response(args.project, response)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 86


if __name__ == "__main__":
    raise SystemExit(main())
