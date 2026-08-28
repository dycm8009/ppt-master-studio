#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

SCHEMA = "ppt-master-studio-mini-app/v1"
RESPONSE_SCHEMA = "ppt-master-studio-mini-app-response/v1"
SUPPORTED_TYPES = {"select", "text", "textarea", "checkbox"}


def _validate(spec: dict) -> dict:
    if spec.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    if not isinstance(spec.get("surface"), str) or not spec["surface"].strip():
        raise ValueError("surface is required")
    if not isinstance(spec.get("title"), str) or not spec["title"].strip():
        raise ValueError("title is required")
    fields = spec.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("fields must be a non-empty array")
    seen: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            raise ValueError("each field must be an object")
        fid = field.get("id")
        ftype = field.get("type")
        if not isinstance(fid, str) or not fid.strip() or fid in seen:
            raise ValueError("field id must be unique and non-empty")
        seen.add(fid)
        if ftype not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported field type: {ftype}")
        if not isinstance(field.get("label"), str) or not field["label"].strip():
            raise ValueError(f"field {fid} requires label")
        if ftype == "select":
            options = field.get("options")
            if not isinstance(options, list) or not options or not all(isinstance(v, str) for v in options):
                raise ValueError(f"select field {fid} requires string options")
            if field.get("value") is not None and field["value"] not in options:
                raise ValueError(f"select field {fid} value must be one of options")
        if ftype == "checkbox" and field.get("value") is not None and not isinstance(field["value"], bool):
            raise ValueError(f"checkbox field {fid} value must be boolean")
    return spec


def _field_markup(field: dict) -> str:
    fid = html.escape(field["id"], quote=True)
    label = html.escape(field["label"])
    help_text = html.escape(str(field.get("help", "")))
    value = field.get("value", "")
    ftype = field["type"]
    helper = f'<div class="help">{help_text}</div>' if help_text else ""

    if ftype == "select":
        options = []
        for option in field["options"]:
            escaped = html.escape(option, quote=True)
            selected = " selected" if option == value else ""
            options.append(f'<option value="{escaped}"{selected}>{html.escape(option)}</option>')
        control = f'<select id="{fid}" data-field="{fid}" data-type="select">{"".join(options)}</select>'
    elif ftype == "textarea":
        control = f'<textarea id="{fid}" data-field="{fid}" data-type="textarea" rows="3">{html.escape(str(value or ""))}</textarea>'
    elif ftype == "checkbox":
        checked = " checked" if bool(value) else ""
        control = f'<label class="switch-row"><input id="{fid}" data-field="{fid}" data-type="checkbox" type="checkbox"{checked}><span>{html.escape(str(field.get("checkbox_label", "Enabled")))}</span></label>'
    else:
        control = f'<input id="{fid}" data-field="{fid}" data-type="text" type="text" value="{html.escape(str(value or ""), quote=True)}">'

    return f'<div class="field"><label for="{fid}">{label}</label>{control}{helper}</div>'


def render(spec: dict) -> str:
    spec = _validate(spec)
    title = html.escape(spec["title"])
    subtitle = html.escape(str(spec.get("subtitle", "")))
    surface = html.escape(spec["surface"], quote=True)
    confirm_label = html.escape(str(spec.get("confirm_label", "Confirm")))
    fields = "\n".join(_field_markup(field) for field in spec["fields"])
    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    meta = json.dumps({"surface": spec["surface"], "response_schema": RESPONSE_SCHEMA}, ensure_ascii=False).replace("</", "<\\/")

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0b0b0c; color: #f5f5f5; padding: 24px; }}
.app {{ max-width: 760px; margin: 0 auto; }}
.badge {{ display:inline-block; border:1px solid #343438; border-radius:999px; padding:6px 10px; font-size:12px; color:#c8c8cc; margin-bottom:16px; }}
h1 {{ font-size: 24px; line-height: 1.2; margin: 0 0 8px; }}
.subtitle {{ margin: 0 0 22px; color:#b8b8bd; line-height:1.6; }}
.panel {{ background:#1c1c1f; border:1px solid #343438; border-radius:18px; padding:20px; box-shadow:0 14px 40px rgba(0,0,0,.22); }}
.field {{ margin-bottom:18px; }}
.field > label {{ display:block; font-size:13px; color:#d6d6da; margin-bottom:8px; font-weight:650; }}
select,input[type=text],textarea {{ width:100%; background:#121214; color:#fff; border:1px solid #3b3b40; border-radius:12px; padding:12px 14px; font:inherit; outline:none; }}
select:focus,input:focus,textarea:focus {{ border-color:#e66c63; box-shadow:0 0 0 3px rgba(230,108,99,.12); }}
.help {{ color:#8f8f95; font-size:12px; margin-top:7px; line-height:1.45; }}
.switch-row {{ display:flex !important; align-items:center; gap:10px; min-height:42px; padding:10px 12px; background:#121214; border:1px solid #3b3b40; border-radius:12px; }}
.actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:6px; }}
button {{ border:0; border-radius:12px; padding:11px 16px; font:inherit; cursor:pointer; }}
#confirm {{ background:#e66c63; color:#111; font-weight:750; }}
#copy {{ background:#303034; color:#fff; }}
#copy[disabled] {{ opacity:.45; cursor:not-allowed; }}
.result-wrap {{ margin-top:18px; display:none; }}
.result-wrap.visible {{ display:block; }}
.result-wrap label {{ display:block; margin-bottom:8px; font-size:12px; color:#bdbdc2; }}
#result {{ min-height:130px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px; }}
.status {{ margin-top:10px; min-height:20px; color:#9fdfa8; font-size:12px; }}
.note {{ margin-top:14px; color:#8d8d93; font-size:12px; line-height:1.5; }}
</style>
</head>
<body>
<div class="app" data-surface="{surface}">
  <div class="badge">PPT Master Studio · Mini App POC</div>
  <h1>{title}</h1>
  {subtitle_html}
  <div class="panel">
    {fields}
    <div class="actions">
      <button id="confirm" type="button">{confirm_label}</button>
      <button id="copy" type="button" disabled>Copy confirmation JSON</button>
    </div>
    <div class="result-wrap" id="resultWrap">
      <label for="result">Confirmation payload</label>
      <textarea id="result" readonly></textarea>
      <div class="status" id="status"></div>
    </div>
    <div class="note">This POC uses ChatGPT's code-block Preview runtime only. It does not assume an undocumented automatic callback to the assistant.</div>
  </div>
</div>
<script>
const META = {meta};
const confirmButton = document.getElementById('confirm');
const copyButton = document.getElementById('copy');
const resultWrap = document.getElementById('resultWrap');
const resultBox = document.getElementById('result');
const statusBox = document.getElementById('status');

function collectValues() {{
  const values = {{}};
  document.querySelectorAll('[data-field]').forEach((node) => {{
    const id = node.dataset.field;
    const type = node.dataset.type;
    values[id] = type === 'checkbox' ? node.checked : node.value;
  }});
  return values;
}}

confirmButton.addEventListener('click', () => {{
  const payload = {{
    schema: META.response_schema,
    surface: META.surface,
    status: 'user-confirmed',
    values: collectValues()
  }};
  resultBox.value = JSON.stringify(payload, null, 2);
  resultWrap.classList.add('visible');
  copyButton.disabled = false;
  statusBox.textContent = 'Confirmed locally in the mini app. Copy the JSON and send it back in chat.';
}});

copyButton.addEventListener('click', async () => {{
  try {{
    await navigator.clipboard.writeText(resultBox.value);
    statusBox.textContent = 'Confirmation JSON copied.';
  }} catch (error) {{
    resultBox.focus();
    resultBox.select();
    statusBox.textContent = 'Clipboard access is unavailable here. The JSON is selected for manual copy.';
  }}
}});
</script>
</body>
</html>'''


def sample_spec() -> dict:
    return {
        "schema": SCHEMA,
        "surface": "stage1-poc",
        "title": "PPT Master Studio · Stage 1",
        "subtitle": "Mini app transport validation only. These fields are sample host data, not a replacement for the official Stage 1 schema.",
        "confirm_label": "确认当前选择",
        "fields": [
            {"id": "audience", "label": "Audience", "type": "select", "value": "C++ developers", "options": ["C++ developers", "Engineering leadership", "Cross-functional team"]},
            {"id": "purpose", "label": "Purpose", "type": "select", "value": "Technical sharing", "options": ["Technical sharing", "Decision review", "Project update"]},
            {"id": "design", "label": "Design", "type": "select", "value": "Free design", "options": ["Free design", "Template"]},
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a self-contained HTML mini app for ChatGPT Interactive Code Block Preview")
    sub = ap.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build")
    build.add_argument("spec", type=Path)
    build.add_argument("--output", type=Path)
    build.add_argument("--code-block", action="store_true", help="emit a fenced html code block instead of raw HTML")

    sample = sub.add_parser("sample")
    sample.add_argument("--output", type=Path)
    sample.add_argument("--code-block", action="store_true")

    args = ap.parse_args()
    spec = sample_spec() if args.cmd == "sample" else json.loads(args.spec.read_text(encoding="utf-8"))
    out = render(spec)
    if args.code_block:
        out = "```html\n" + out + "\n```"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
