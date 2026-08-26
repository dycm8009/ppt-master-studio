from .base import *

def catalogs() -> dict:
    return read_json(CATALOGS_PATH)


def animation_registries() -> tuple[list[str], list[str]]:
    proc = subprocess.run(
        [sys.executable, str(UPSTREAM_SCRIPT_DIR / "pptx_animations.py"), "--list"],
        text=True, capture_output=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise ValueError(f"cannot read animation registry: {proc.stderr.strip()}")
    transitions, objects, section = ["none"], ["none"], None
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s == "Available transition effects:": section = "transition"; continue
        if s.startswith("Legacy compatibility inputs"): section = None; continue
        if s == "Available object animations:": section = "object"; continue
        m = re.match(r"^\s{4}([a-z0-9_]+):", line)
        if not m: continue
        effect = m.group(1)
        if section == "transition" and effect not in transitions: transitions.append(effect)
        if section == "object" and effect not in objects: objects.append(effect)
    if len(transitions) < 10 or len(objects) < 50:
        raise ValueError("animation registry parse returned an unexpectedly small catalog")
    return transitions, objects


BASE_CSS = """
:root{font-family:Inter,system-ui,sans-serif;color:#172033;background:#eef1f5}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1180px;margin:auto;padding:24px 22px 90px}
.top{position:sticky;top:0;z-index:10;background:#eef1f5ee;padding:14px 0;border-bottom:1px solid #d7dce4}
h1,h2,h3{margin-top:0}.sub,.hint,.small,.preview-caption{color:#68778a}.hint,.small,.preview-caption{font-size:12px}
.card{background:#fff;border:1px solid #dce2ea;border-radius:14px;padding:16px;margin-top:16px;box-shadow:0 4px 18px #1420330a}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.field{margin:12px 0}.field label{display:block;font-weight:700;margin-bottom:6px}
textarea,input,select{width:100%;font:inherit;border:1px solid #cbd3df;border-radius:9px;padding:10px;background:#fff;color:#172033}
textarea{min-height:82px;resize:vertical}input[type=checkbox],input[type=radio]{width:auto}
.choice{display:flex;gap:8px;padding:9px;border:1px solid #d9e0e8;border-radius:9px;margin:7px 0;background:#fafbfd}
.direction{cursor:pointer;overflow:hidden}.direction.active{outline:3px solid #5e6ad2;border-color:#5e6ad2}
.direction-preview-frame,.style-sample{aspect-ratio:16/9;border:1px solid #d9e0e8;border-radius:10px;overflow:hidden;background:#f6f8fb;margin:10px 0}
.direction-preview-frame img,.style-sample img{width:100%;height:100%;object-fit:cover;display:block}
.semantic-preview,.strategy-readout{border:1px solid #d9e0e8;border-radius:10px;background:#f8fafc;padding:10px;margin:8px 0 12px}
.strategy-readout.warning{background:#fffbeb;border-color:#f4d37d;color:#805b10}
.mode-mini{width:100%;aspect-ratio:16/5;border:1px solid #e1e6ed;border-radius:9px;background:#fff;overflow:hidden}.mode-mini svg{width:100%;height:100%}
.icon-preview-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.icon-preview-cell{border:1px solid #dce2ea;border-radius:9px;background:#fff;padding:8px;text-align:center}.icon-preview-mark svg{width:38px;height:38px}.icon-preview-name{font-size:10px;color:#718096;word-break:break-all}
.palette{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.row{display:flex;gap:10px;align-items:center}.row>*{flex:1}
.btn{border:0;border-radius:9px;padding:10px 16px;font-weight:700;cursor:pointer;background:#252f3f;color:#fff}.btn.secondary{background:#e8edf4;color:#223047}
.output{min-height:210px;font-family:ui-monospace,monospace;font-size:12px;white-space:pre}
.bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #d8dee8;padding:12px 18px;z-index:20}.bar .inner{max-width:1180px;margin:auto;display:flex;gap:10px}
.slide-layout{display:grid;grid-template-columns:180px minmax(0,1fr) 280px;gap:14px}.slides{max-height:70vh;overflow:auto}.slide-thumb{padding:8px;border:1px solid #d7dde6;border-radius:8px;margin:6px 0;cursor:pointer;background:#fff}.slide-thumb.active{border-color:#5e6ad2;background:#f0f1ff}.stage{background:#111827;border-radius:12px;padding:12px;overflow:auto;min-height:500px}.stage svg{width:100%;height:auto;background:#fff}.selected{outline:2px solid #ff7a00}
@media(max-width:850px){.grid,.grid3,.slide-layout{grid-template-columns:1fr}.bar,.top{position:static}.shell{padding-bottom:28px}}
"""

COPY_JS = """
function copyOutput(){const t=document.getElementById('output');t.select();navigator.clipboard?.writeText(t.value).catch(()=>document.execCommand('copy'));}
function putOutput(obj){const t=document.getElementById('output');t.value=JSON.stringify(obj,null,2);document.getElementById('output-card').scrollIntoView({behavior:'smooth'});}
"""


def html_doc(title: str, body: str, data: dict | None = None, extra_js: str = "") -> str:
    block = "" if data is None else f'<script id="adapter-data" type="application/json">{js_json(data)}</script>'
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{BASE_CSS}</style></head><body>{block}{body}<script>{COPY_JS}\n{extra_js}</script></body></html>'


def output_card() -> str:
    return '<section class="card" id="output-card"><h2>确认输出</h2><p class="hint">生成后将完整 JSON 复制回 ChatGPT；这是 Static UI 用户确认，不是官方 Flask 回执。</p><textarea id="output" class="output" spellcheck="false"></textarea><div style="margin-top:10px"><button class="btn secondary" onclick="copyOutput()">复制 JSON</button></div></section>'
