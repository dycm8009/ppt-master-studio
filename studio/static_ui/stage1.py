from .base import *
from .templates import *
from .assets import *
def stage1_html(project: Path) -> str:
    rec = read_json(project / "confirm_ui" / "recommendations.stage1.json")
    if rec.get("stage") != "stage1": raise ValueError("recommendations.stage1.json does not declare stage1")
    opts, _ = build_template_options(project); cats = catalogs()
    lang = str(rec.get("primary_language") or opts.get("lang") or "zh-CN"); ui = stage1_locale(lang)
    prose = [("audience","受众"),("communication_intent","沟通意图"),("audience_outcome","期望受众结果"),("core_message","核心信息"),("delivery_context","主要使用场景"),("artifact_afterlife","材料后续用途"),("content_divergence","对原始内容的处理方式")]
    fields = "".join(f'<div class="field"><label for="{k}">{label}</label><textarea id="{k}">{html.escape(str(value_of(rec,k,"")))}</textarea></div>' for k,label in prose)
    recommended_canvas = (rec.get("recommend") or {}).get("canvas", "ppt169")
    canvas_opts = "".join(f'<option value="{html.escape(str(c.get("id")))}" {"selected" if c.get("id")==recommended_canvas else ""}>{html.escape(localized(c,lang,str(c.get("id"))))} · {html.escape(str(c.get("dim", "")))}</option>' for c in cats.get("canvas", []) if isinstance(c,dict))
    candidate_cards=[]
    for kind in ("brand","style","layout","deck"):
        choices=[f'<option value="">{html.escape(ui["none"])}</option>']
        for c in opts.get("library",{}).get(kind,[]):
            name,summary=template_display(kind,c,lang); tail=f" — {summary}" if summary else ""
            choices.append(f'<option value="{html.escape(c["key"])}">{html.escape(name+tail)}</option>')
        candidate_cards.append(f'<div class="field"><label>{html.escape(ui[kind])}</label><select class="template-select" data-kind="{kind}">{"".join(choices)}</select></div>')
    explicit=opts.get("explicit",[])
    if explicit:
        grouped={}
        for c in explicit: grouped.setdefault(c["workspace_root"],[]).append(c)
        choices=[f'<option value="">{html.escape(ui["none"])}</option>']; labels={"brand":ui["brand"],"style":ui["style"],"layout":ui["layout"],"deck":ui["deck"]}
        for root,items in grouped.items():
            keys="|".join(c["key"] for c in items); kinds="、".join(labels.get(c["kind"],c["kind"]) for c in items); label=items[0].get("label",Path(root).name or root)
            choices.append(f'<option value="{html.escape(root)}" data-keys="{html.escape(keys)}">{html.escape(label)}（{html.escape(kinds)}）</option>')
        candidate_cards.append(f'<div class="field"><label>{html.escape(ui["specified"])}</label><select id="explicit-select">{"".join(choices)}</select></div>')
    data={"recommendation":rec,"template_options":opts,"recommendation_sha256":digest(rec)}
    body=f'''<main class="shell"><header class="top"><h1>Stage 1 · 内容沟通 + 模板确认</h1><p class="sub">保留、修改或清空推荐值。这里确认的是“我们要讲什么、给谁讲、用什么模板边界”。</p></header><section class="card"><h2>沟通合同</h2>{fields}<div class="field"><label>{html.escape(ui['primary_language'])}</label><input id="primary_language" value="{html.escape(str(rec.get('primary_language','zh-CN')))}"></div><div class="field"><label>{html.escape(ui['canvas'])}</label><select id="canvas">{canvas_opts}</select></div></section><section class="card"><h2>模板模式</h2><label class="choice"><input type="radio" name="template-mode" value="free_design" {'checked' if opts.get('default_mode')=='free_design' else ''}><span><b>{html.escape(ui['free_design'])}</b><div class="hint">{html.escape(ui['free_design_hint'])}</div></span></label><label class="choice"><input type="radio" name="template-mode" value="templates" {'checked' if opts.get('default_mode')=='templates' else ''}><span><b>{html.escape(ui['use_templates'])}</b><div class="hint">{html.escape(ui['use_templates_hint'])}</div></span></label><div id="template-panel">{"".join(candidate_cards)}</div></section>{output_card()}</main><div class="bar"><div class="inner"><button class="btn" onclick="generateStage1()">确认并生成回传 JSON</button><span id="status" class="hint"></span></div></div>'''
    js=r'''
const DATA=JSON.parse(document.getElementById('adapter-data').textContent);
function chosenMode(){const n=document.querySelector('input[name="template-mode"]:checked');return n?n.value:'free_design'}
function syncPanel(){document.getElementById('template-panel').style.display=chosenMode()==='templates'?'block':'none'}
document.querySelectorAll('input[name="template-mode"]').forEach(n=>n.addEventListener('change',syncPanel));
function preselect(){const keys=new Set(DATA.template_options.preselected_keys||[]);document.querySelectorAll('.template-select').forEach(sel=>{for(const o of sel.options){if(keys.has(o.value)){sel.value=o.value;break;}}});const ex=document.getElementById('explicit-select');if(ex){for(const o of ex.options){const ks=(o.dataset.keys||'').split('|').filter(Boolean);if(ks.length&&ks.every(k=>keys.has(k))){ex.value=o.value;break;}}}syncPanel()}
function selectedKeys(){if(chosenMode()!=='templates')return[];const out=[];document.querySelectorAll('.template-select').forEach(sel=>{if(sel.value)out.push(sel.value)});const ex=document.getElementById('explicit-select');if(ex&&ex.value){const o=ex.options[ex.selectedIndex];out.push(...(o.dataset.keys||'').split('|').filter(Boolean));}return [...new Set(out)]}
function generateStage1(){const keys=selectedKeys();if(chosenMode()==='templates'&&!keys.length){document.getElementById('status').textContent='模板模式至少选择一个模板';return}const v={stage:'stage1',primary_language:document.getElementById('primary_language').value,canvas:document.getElementById('canvas').value,audience:document.getElementById('audience').value,communication_intent:document.getElementById('communication_intent').value,audience_outcome:document.getElementById('audience_outcome').value,core_message:document.getElementById('core_message').value,delivery_context:document.getElementById('delivery_context').value,artifact_afterlife:document.getElementById('artifact_afterlife').value,content_divergence:document.getElementById('content_divergence').value,template_selection:{mode:chosenMode(),selection_keys:keys}};putOutput({schema:'ppt-master-chat-confirm/v1',surface:'stage1',status:'user-confirmed',recommendation_sha256:DATA.recommendation_sha256,options_sha256:DATA.template_options.options_sha256,values:v});document.getElementById('status').textContent='已生成，可复制回 ChatGPT'}
preselect();
'''
    return html_doc("PPT Master 阶段 1 静态确认",body,data,js)
