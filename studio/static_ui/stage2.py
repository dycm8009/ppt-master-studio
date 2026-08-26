from .base import *
from .assets import *
from .previews import *
from .stage2_js import STAGE2_JS
def stage2_html(project: Path) -> str:
    rec = read_json(project / "confirm_ui" / "recommendations.stage2.json")
    if rec.get("stage") != "stage2": raise ValueError("recommendations.stage2.json does not declare stage2")
    cats = catalogs(); lang = str(rec.get("lang") or "zh")
    zh = lang.lower().startswith("zh")
    directions = (rec.get("design_directions") or {}).get("candidates") or []
    if len(directions) != 3: raise ValueError("Stage 2 requires exactly three design_directions candidates")
    selected = (rec.get("design_directions") or {}).get("selected",0)
    if type(selected) is not int or selected not in (0,1,2): selected=0
    direction_html=[]
    for i,d in enumerate(directions):
        name=localized(d,lang,f"Direction {i+1}")
        note=d.get("note_zh") or d.get("note_en") or d.get("note") or d.get("visual_style_behavior_zh") or d.get("visual_style_behavior_en") or ""
        palette=(d.get("color") or {}).get("palette") or {}
        swatches="".join(f'<span style="display:inline-block;width:22px;height:22px;border-radius:5px;background:{html.escape(str(palette.get(r,"#ddd")))};border:1px solid #ccd"></span>' for r in PALETTE_ROLES)
        preview_uri, preview_caption = direction_preview_uri(d, lang)
        badge=("推荐" if i==selected else f"方案 {i+1}") if zh else ("Recommended" if i==selected else f"Option {i+1}")
        direction_html.append(f'<div class="card direction {"active" if i==selected else ""}" data-i="{i}" onclick="selectDirection({i})"><div class="tag">{badge}</div><h3>{html.escape(name)}</h3><div class="direction-preview-frame"><img src="{preview_uri}" alt="design direction preview"></div><div class="preview-caption">{html.escape(preview_caption)}</div><p>{html.escape(str(note))}</p><div>{swatches}</div></div>')
    mode_opts=[f'<option value="custom">{"自定义" if zh else "Custom"}</option>']+[f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("modes",[]) if isinstance(x,dict)]
    style_opts=[f'<option value="custom">{"自定义" if zh else "Custom"}</option>']+[f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in flatten_visual_styles(cats)]
    icon_opts=[f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("icons",[]) if isinstance(x,dict)]
    delivery_opts=[f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("delivery_purpose",[]) if isinstance(x,dict)]
    usage_checks=''.join(f'<label class="choice"><input type="checkbox" name="image_usage" value="{html.escape(str(x.get("id")))}"><span>{html.escape(localized(x,lang,str(x.get("id"))))}</span></label>' for x in cats.get("image_usage",[]) if isinstance(x,dict))
    ai_opts=''.join(f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("image_ai_path",[]) if isinstance(x,dict))
    gen_opts=''.join(f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("generation_mode",[]) if isinstance(x,dict))
    font_opts=''.join(f'<option value="{html.escape(str(x.get("id")))}">{html.escape(localized(x,lang,str(x.get("id"))))}</option>' for x in cats.get("fonts",[]) if isinstance(x,dict))
    palette_labels={'background':'背景','secondary_bg':'次级背景','primary':'主色','accent':'强调色','secondary_accent':'次强调色','body_text':'正文色'} if zh else {r:r for r in PALETTE_ROLES}
    palette_fields=''.join(f'<div class="field"><label>{palette_labels[r]}</label><input id="color_{r}" type="color"></div>' for r in PALETTE_ROLES)
    template_field=''
    if isinstance(rec.get('template_application'),dict):
        template_field=f'<div class="field"><label>{"模板应用说明" if zh else "Template Application"}</label><textarea id="template_application">{html.escape(str(value_of(rec,"template_application","")))}</textarea></div>'
    style_preview_data={}
    for x in flatten_visual_styles(cats):
        if isinstance(x,dict):
            sid=str(x.get("id") or "")
            uri=official_style_preview_uri(sid)
            if uri: style_preview_data[sid]=uri
    direction_preview_data=[direction_preview_uri(d,lang)[0] for d in directions]
    data={"recommendation":rec,"catalogs":cats,"recommendation_sha256":digest(rec),"selected_direction":selected,"style_preview_data":style_preview_data,"direction_preview_data":direction_preview_data,"mode_preview_catalog":mode_preview_catalog(cats,lang),"icon_preview_data":icon_preview_samples(),"lang":lang}
    body=f'''<main class="shell"><header class="top"><h1>Stage 2 · 最终设计与生产方案</h1><p class="sub">先看整页样本选择成套方向，再按需要微调。样本用于比较整体视觉，不代表最终页面版式。</p></header><section><div class="grid3">{"".join(direction_html)}</div></section><section class="card"><h2>内容与阅读方式</h2>{template_field}<div class="grid"><div class="field"><label>页数</label><input id="page_count" value="{html.escape(str(value_of(rec,'page_count','')))}"></div><div class="field"><label>阅读模式</label><select id="delivery_purpose">{"".join(delivery_opts)}</select></div></div></section><section class="card"><h2>视觉系统</h2><div class="grid"><div><div class="field"><label>表达模式</label><select id="mode">{"".join(mode_opts)}</select></div><div id="mode_preview" class="semantic-preview"></div><div class="field" id="mode_behavior_field"><label>自定义表达模式规则</label><textarea id="mode_behavior"></textarea><div class="hint">官方三套整套方向通常使用 custom：它保存项目专属的叙事/论证骨架；下拉中的五个固定模式是手动替代选项。</div></div><div class="field"><label>视觉风格</label><select id="visual_style">{"".join(style_opts)}</select></div><div id="visual_style_preview" class="style-sample"></div><div class="field" id="visual_style_behavior_field"><label>自定义视觉风格规则</label><textarea id="visual_style_behavior"></textarea></div><div class="field"><label>图标体系</label><select id="icons">{"".join(icon_opts)}</select></div><div id="icon_preview" class="semantic-preview"></div></div><div><h3>配色与字体</h3><div class="palette">{palette_fields}</div><div class="field"><label>标题字体</label><select id="heading_font">{font_opts}</select></div><div class="field"><label>英文标题字体</label><select id="heading_english">{font_opts}</select></div><div class="field"><label>正文字体</label><select id="body_font">{font_opts}</select></div><div class="field"><label>英文正文字体</label><select id="body_english">{font_opts}</select></div><div class="row"><div class="field"><label>正文 px</label><input id="body_size" type="number" min="8"></div><div class="field"><label>标题 px</label><input id="size_title" type="number"></div><div class="field"><label>副标题 px</label><input id="size_subtitle" type="number"></div><div class="field"><label>注释 px</label><input id="size_annotation" type="number"></div></div></div></div></section><section class="card"><h2>图片策略</h2><div class="grid"><div>{usage_checks}<div id="image_usage_readout" class="strategy-readout"></div></div><div><div class="field"><label>图片使用说明</label><textarea id="image_notes">{html.escape(str(value_of(rec,'image_notes','')))}</textarea><div class="hint">来源选择定义“允许从哪里获取”；使用说明定义“什么时候用、用来做什么”。修改来源不会自动覆盖你写的说明。</div></div><div id="image_notes_warning" class="strategy-readout" style="display:none"></div><div id="ai-controls"><div class="field"><label>AI 图片路径</label><select id="image_ai_path">{ai_opts}</select></div><div class="field"><label>生成图片风格</label><input id="image_rendering" value="custom"></div><div class="field"><label>图片渲染规则</label><textarea id="image_behavior"></textarea></div></div></div></div></section><section class="card"><h2>生产选项</h2><div class="grid"><label class="choice"><input id="speaker_notes" type="checkbox"><span>主动生成 Speaker Notes</span></label><label class="choice"><input id="custom_animations" type="checkbox"><span>主动进行 Custom Animations</span></label><label class="choice"><input id="narration" type="checkbox"><span>主动生成 Narration Audio</span></label><label class="choice"><input id="refine_spec" type="checkbox"><span>生成 Design Spec 后在聊天中继续 Review</span></label></div><div class="field"><label>生成模式</label><select id="generation_mode">{gen_opts}</select></div></section>{output_card()}</main><div class="bar"><div class="inner"><button class="btn" onclick="generateStage2()">确认并生成回传 JSON</button><span id="status" class="hint"></span></div></div>'''
    js=STAGE2_JS
    return html_doc("PPT Master Stage 2 Static Confirm",body,data,js)
