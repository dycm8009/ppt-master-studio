from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from studio.static_ui.assets import catalogs
from studio.static_ui.base import PALETTE_ROLES, digest, localized, read_json, value_of
from studio.static_ui.previews import (
    direction_preview_uri,
    flatten_visual_styles,
    icon_preview_samples,
    mode_preview_catalog,
    official_style_preview_uri,
)


STAGE2_MODEL_SCHEMA = "ppt-master-chat-inline-stage2-model/v1"


def _desc(item: dict[str, Any], lang: str) -> str:
    lang_l = str(lang).lower()
    if lang_l.startswith("zh-tw") or lang_l.startswith("zh-hant"):
        keys = ("desc_zh_tw", "desc_zh", "desc_en")
    elif lang_l.startswith("zh"):
        keys = ("desc_zh", "desc_zh_tw", "desc_en")
    elif lang_l.startswith("ja"):
        keys = ("desc_ja", "desc_en")
    else:
        keys = ("desc_en", "desc_zh")
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _catalog_rows(items: Any, lang: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in items or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        item_id = str(item["id"])
        rows.append(
            {
                "id": item_id,
                "label": localized(item, lang, item_id),
                "desc": _desc(item, lang),
            }
        )
    return rows


def stage2_artifact_model(project: Path) -> dict[str, Any]:
    """Build the chat-inline Stage 2 model from the exact Static UI sources.

    The model intentionally reuses the official catalogs and preview helpers rather
    than defining a second option universe for the artifact host.
    """
    project = project.resolve()
    rec = read_json(project / "confirm_ui" / "recommendations.stage2.json")
    if rec.get("stage") != "stage2":
        raise ValueError("recommendations.stage2.json does not declare stage2")

    cats = catalogs()
    lang = str(rec.get("lang") or "zh")
    directions_raw = (rec.get("design_directions") or {}).get("candidates") or []
    if len(directions_raw) != 3 or any(not isinstance(item, dict) for item in directions_raw):
        raise ValueError("Stage 2 requires exactly three design_directions candidates")
    selected = (rec.get("design_directions") or {}).get("selected", 0)
    if type(selected) is not int or selected not in (0, 1, 2):
        selected = 0

    directions: list[dict[str, Any]] = []
    for index, candidate in enumerate(directions_raw):
        preview_uri, preview_caption = direction_preview_uri(candidate, lang)
        note = (
            candidate.get("note_zh")
            or candidate.get("note_en")
            or candidate.get("note")
            or candidate.get("visual_style_behavior_zh")
            or candidate.get("visual_style_behavior_en")
            or ""
        )
        directions.append(
            {
                "index": index,
                "label": localized(candidate, lang, f"Direction {index + 1}"),
                "note": str(note),
                "preview_uri": preview_uri,
                "preview_caption": preview_caption,
                "candidate": candidate,
            }
        )

    styles = []
    for item in flatten_visual_styles(cats):
        style_id = str(item.get("id") or "")
        if not style_id:
            continue
        styles.append(
            {
                "id": style_id,
                "label": localized(item, lang, style_id),
                "desc": _desc(item, lang),
                "preview_uri": official_style_preview_uri(style_id),
            }
        )

    recommend = rec.get("recommend") or {}
    raw_usage = recommend.get("image_usage", "none")
    image_usage = list(raw_usage) if isinstance(raw_usage, list) else [str(raw_usage or "none")]

    template_application = None
    if isinstance(rec.get("template_application"), dict):
        template_application = str(value_of(rec, "template_application", ""))

    return {
        "schema": STAGE2_MODEL_SCHEMA,
        "surface": "stage2",
        "language": lang,
        "recommendation_sha256": digest(rec),
        "selected_direction": selected,
        "directions": directions,
        "catalogs": {
            "modes": mode_preview_catalog(cats, lang),
            "visual_styles": styles,
            "icons": _catalog_rows(cats.get("icons"), lang),
            "delivery_purpose": _catalog_rows(cats.get("delivery_purpose"), lang),
            "image_usage": _catalog_rows(cats.get("image_usage"), lang),
            "image_ai_path": _catalog_rows(cats.get("image_ai_path"), lang),
            "generation_mode": _catalog_rows(cats.get("generation_mode"), lang),
            "fonts": _catalog_rows(cats.get("fonts"), lang),
        },
        "icon_preview_data": icon_preview_samples(),
        "defaults": {
            "page_count": str(value_of(rec, "page_count", "")),
            "delivery_purpose": str(recommend.get("delivery_purpose") or "balanced"),
            "image_usage": image_usage,
            "image_notes": str(value_of(rec, "image_notes", "")),
            "image_ai_path": str(recommend.get("image_ai_path") or "auto"),
            "generation_mode": str(recommend.get("generation_mode") or "continuous"),
            "proactive_speaker_notes": bool(value_of(rec, "proactive_speaker_notes", True)),
            "proactive_custom_animations": bool(value_of(rec, "proactive_custom_animations", False)),
            "proactive_narration_audio": bool(value_of(rec, "proactive_narration_audio", False)),
            "refine_spec": bool(value_of(rec, "refine_spec", False)),
            "template_application": template_application,
        },
        "authority": {
            "capture_schema": "ppt-master-chat-confirm/v1",
            "capture_surface": "stage2",
            "accepted_schema": "ppt-master-static-ui-accepted/v1",
            "validator": "studio/scripts/static_ui_adapter.py validate",
            "contract_source": "studio.static_ui.validators.validate_stage2",
            "catalog_source": "skills/ppt-master/scripts/confirm_ui/static/catalogs.json",
        },
    }


def _pick(candidate: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def stage2_default_values(model: dict[str, Any], selected_direction: int | None = None) -> dict[str, Any]:
    """Return the validator-shaped values represented by the selected recommendation.

    This is used for parity tests and host packaging; the browser artifact may edit
    every exposed field before constructing the same shape locally.
    """
    if model.get("schema") != STAGE2_MODEL_SCHEMA:
        raise ValueError("not a Stage 2 chat-inline artifact model")
    index = model["selected_direction"] if selected_direction is None else selected_direction
    if type(index) is not int or index not in (0, 1, 2):
        raise ValueError("selected_direction must be 0, 1 or 2")
    candidate = model["directions"][index]["candidate"]
    defaults = model["defaults"]
    palette = dict((candidate.get("color") or {}).get("palette") or {})
    typography = candidate.get("typography") or {}
    heading = typography.get("heading") or {}
    body = typography.get("body") or {}
    body_size = typography.get("body_size") or 24
    sizes = typography.get("sizes") or {}
    values: dict[str, Any] = {
        "stage": "final",
        "page_count": str(defaults.get("page_count") or ""),
        "delivery_purpose": str(defaults["delivery_purpose"]),
        "mode": str(candidate.get("mode") or "custom"),
        "visual_style": str(candidate.get("visual_style") or "custom"),
        "color": {"name": "static-ui-selection", "palette": palette},
        "icons": str(candidate.get("icons") or "none"),
        "typography": {
            "name": "static-ui-selection",
            "heading": {
                "primary": str(heading.get("primary") or heading.get("english") or "Arial"),
                "english": str(heading.get("english") or heading.get("primary") or "Arial"),
                "css": "sans-serif",
            },
            "body": {
                "primary": str(body.get("primary") or body.get("english") or "Arial"),
                "english": str(body.get("english") or body.get("primary") or "Arial"),
                "css": "sans-serif",
            },
            "body_size": body_size,
            "body_size_unit": "px",
            "sizes": {
                "title": sizes.get("title") or round(float(body_size) * 1.75),
                "subtitle": sizes.get("subtitle") or round(float(body_size) * 1.33),
                "annotation": sizes.get("annotation") or round(float(body_size) * 0.75),
            },
        },
        "image_usage": list(defaults.get("image_usage") or ["none"]),
        "image_notes": str(defaults.get("image_notes") or ""),
        "proactive_speaker_notes": bool(defaults.get("proactive_speaker_notes")),
        "proactive_custom_animations": bool(defaults.get("proactive_custom_animations")),
        "proactive_narration_audio": bool(defaults.get("proactive_narration_audio")),
        "generation_mode": str(defaults["generation_mode"]),
        "refine_spec": bool(defaults.get("refine_spec")),
    }
    if values["mode"] == "custom":
        values["mode_behavior"] = _pick(candidate, "mode_behavior_zh", "mode_behavior_en", "mode_behavior")
    if values["visual_style"] == "custom":
        values["visual_style_behavior"] = _pick(
            candidate,
            "visual_style_behavior_zh",
            "visual_style_behavior_en",
            "visual_style_behavior",
        )
    if defaults.get("template_application") is not None:
        values["template_application"] = str(defaults["template_application"])
    if "ai" in values["image_usage"]:
        strategy = candidate.get("image_strategy") or {}
        values["image_ai_path"] = str(defaults.get("image_ai_path") or "auto")
        values["image_strategy"] = {
            "name": "static-ui-selection",
            "rendering": str(strategy.get("rendering") or "custom"),
            "behavior": _pick(strategy, "behavior_zh", "behavior_en", "behavior"),
        }
    return values


def stage2_default_capture(model: dict[str, Any], selected_direction: int | None = None) -> dict[str, Any]:
    return {
        "schema": "ppt-master-chat-confirm/v1",
        "surface": "stage2",
        "status": "user-confirmed",
        "recommendation_sha256": model["recommendation_sha256"],
        "values": stage2_default_values(model, selected_direction),
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _options(rows: list[dict[str, Any]], *, include_custom: bool = False) -> str:
    out = ['<option value="custom">自定义 Custom</option>'] if include_custom else []
    for row in rows:
        out.append(f'<option value="{_e(row["id"])}">{_e(row.get("label") or row["id"])}</option>')
    return "".join(out)


def _model_text(model: dict[str, Any]) -> str:
    return html.escape(json.dumps(model, ensure_ascii=False, separators=(",", ":")), quote=False)


def stage2_artifact_fragment(model: dict[str, Any]) -> str:
    if model.get("schema") != STAGE2_MODEL_SCHEMA:
        raise ValueError("not a Stage 2 chat-inline artifact model")
    directions = model["directions"]
    if len(directions) != 3:
        raise ValueError("Stage 2 artifact requires exactly three design directions")
    cats = model["catalogs"]
    defaults = model["defaults"]
    selected = model["selected_direction"]

    direction_html = "".join(
        f'''<button type="button" class="pm-s2-dir {"active" if i == selected else ""}" data-index="{i}">
<div class="pm-s2-badge">{"推荐" if i == selected else f"方案 {i + 1}"}</div><div class="pm-s2-name">{_e(d["label"])}</div>
<div class="pm-s2-sample"><img src="{_e(d["preview_uri"])}" alt="design direction preview"></div>
<div class="pm-s2-caption">{_e(d["preview_caption"])}</div><div class="pm-s2-note">{_e(d["note"])}</div></button>'''
        for i, d in enumerate(directions)
    )
    image_checks = "".join(
        f'<label class="pm-s2-choice"><input type="checkbox" name="pm-s2-image-usage" value="{_e(row["id"])}"><span><b>{_e(row["label"])}</b><small>{_e(row.get("desc", ""))}</small></span></label>'
        for row in cats["image_usage"]
    )
    palette_fields = "".join(
        f'<div><label>{_e(role)}</label><input id="pm-s2-color-{_e(role)}" type="color" class="pm-s2-input"></div>'
        for role in PALETTE_ROLES
    )
    template_field = ""
    if defaults.get("template_application") is not None:
        template_field = f'<div class="pm-s2-wide"><label>模板应用说明 Template Application</label><textarea id="pm-s2-template-application" class="pm-s2-input">{html.escape(str(defaults["template_application"]))}</textarea></div>'

    return f'''<div id="pm-stage2-parity" class="pm-s2-root">
<style>
#pm-stage2-parity{{width:100%;color:var(--viz-text)}}#pm-stage2-parity *{{box-sizing:border-box}}#pm-stage2-parity .pm-s2-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;margin-bottom:12px}}#pm-stage2-parity .pm-s2-title{{font-weight:750}}#pm-stage2-parity .pm-s2-muted,#pm-stage2-parity small{{display:block;font-size:11px;color:var(--viz-muted);font-weight:400}}#pm-stage2-parity .pm-s2-pill{{font-size:12px;border:1px solid var(--viz-border);border-radius:999px;padding:6px 9px;color:var(--viz-muted)}}#pm-stage2-parity .pm-s2-pill.ok{{border-color:var(--viz-accent);background:var(--viz-accent-bg);color:var(--viz-text)}}#pm-stage2-parity .pm-s2-dirs{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}#pm-stage2-parity .pm-s2-dir{{text-align:left;color:var(--viz-text);border:1px solid var(--viz-border);border-radius:13px;background:var(--viz-card);padding:10px;cursor:pointer;min-width:0}}#pm-stage2-parity .pm-s2-dir.active{{border-color:var(--viz-accent);box-shadow:0 0 0 2px var(--viz-accent-bg)}}#pm-stage2-parity .pm-s2-badge{{font-size:10px;color:var(--viz-muted)}}#pm-stage2-parity .pm-s2-name{{font-size:14px;font-weight:750;margin:3px 0 6px}}#pm-stage2-parity .pm-s2-sample{{aspect-ratio:16/9;border:1px solid var(--viz-border);border-radius:9px;overflow:hidden;background:var(--viz-panel)}}#pm-stage2-parity .pm-s2-sample img{{width:100%;height:100%;object-fit:cover;display:block}}#pm-stage2-parity .pm-s2-caption{{font-size:10px;color:var(--viz-muted);margin-top:5px}}#pm-stage2-parity .pm-s2-note{{font-size:12px;color:var(--viz-muted);line-height:1.4;margin-top:6px}}#pm-stage2-parity .pm-s2-card{{border:1px solid var(--viz-border);border-radius:13px;background:var(--viz-card);padding:12px;margin-top:12px}}#pm-stage2-parity .pm-s2-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}#pm-stage2-parity .pm-s2-wide{{grid-column:1/-1}}#pm-stage2-parity label{{display:block;font-size:12px;font-weight:650;color:var(--viz-muted);margin:8px 0 4px}}#pm-stage2-parity .pm-s2-input{{width:100%;min-width:0;border:1px solid var(--viz-border);background:var(--viz-panel);color:var(--viz-text);border-radius:9px;padding:8px 9px;font-size:13px;outline:none}}#pm-stage2-parity textarea.pm-s2-input{{resize:vertical;min-height:68px}}#pm-stage2-parity .pm-s2-input:focus{{border-color:var(--viz-accent);box-shadow:0 0 0 2px var(--viz-accent-bg)}}#pm-stage2-parity .pm-s2-preview{{border:1px solid var(--viz-border);border-radius:9px;background:var(--viz-panel);padding:8px;margin-top:7px;font-size:12px;color:var(--viz-muted)}}#pm-stage2-parity .pm-s2-style-preview img{{display:block;width:100%;aspect-ratio:16/5;object-fit:cover;border-radius:7px;margin-top:6px}}#pm-stage2-parity .pm-s2-icons{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:7px}}#pm-stage2-parity .pm-s2-icon{{border:1px solid var(--viz-border);border-radius:7px;padding:6px;text-align:center;background:var(--viz-card)}}#pm-stage2-parity .pm-s2-icon svg{{width:30px;height:30px}}#pm-stage2-parity .pm-s2-choice{{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--viz-border);border-radius:9px;padding:8px;background:var(--viz-panel)}}#pm-stage2-parity .pm-s2-choice input{{width:auto;margin-top:2px}}#pm-stage2-parity .pm-s2-checks{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}}#pm-stage2-parity .pm-s2-actions{{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;border-top:1px solid var(--viz-border);padding-top:12px;margin-top:12px}}#pm-stage2-parity button.pm-s2-btn{{min-height:42px;border-radius:9px;padding:8px 12px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid var(--viz-border);background:var(--viz-card);color:var(--viz-text)}}#pm-stage2-parity button.pm-s2-btn.primary{{background:var(--viz-accent);border-color:var(--viz-accent);color:white}}#pm-stage2-parity .pm-s2-capture{{margin-top:10px;border:1px solid var(--viz-accent);background:var(--viz-accent-bg);border-radius:10px;padding:9px}}#pm-stage2-parity .pm-s2-output{{width:100%;min-height:110px;margin-top:8px;font:11px ui-monospace,monospace}}#pm-stage2-parity .hidden{{display:none}}@media(max-width:760px){{#pm-stage2-parity .pm-s2-dirs,#pm-stage2-parity .pm-s2-grid{{grid-template-columns:1fr}}#pm-stage2-parity .pm-s2-wide{{grid-column:auto}}}}
</style>
<div class="pm-s2-head"><div><div class="pm-s2-title">Stage 2 · 最终设计与生产方案</div><div class="pm-s2-muted">与 PPT Master Static UI 同源的 catalogs / previews / response contract</div></div><span id="pm-s2-status" class="pm-s2-pill">Draft · not validated</span></div>
<div class="pm-s2-dirs">{direction_html}</div>
<div class="pm-s2-card"><b>内容与阅读方式</b><div class="pm-s2-grid">{template_field}<div><label>页数 Page Count</label><input id="pm-s2-page-count" class="pm-s2-input" value="{_e(defaults["page_count"])}"></div><div><label>阅读模式 Delivery Purpose</label><select id="pm-s2-delivery" class="pm-s2-input">{_options(cats["delivery_purpose"])}</select></div></div></div>
<div class="pm-s2-card"><b>视觉系统</b><div class="pm-s2-grid"><div><label>表达模式 Mode</label><select id="pm-s2-mode" class="pm-s2-input">{_options(cats["modes"], include_custom=True)}</select><div id="pm-s2-mode-preview" class="pm-s2-preview"></div><div id="pm-s2-mode-behavior-wrap"><label>自定义表达模式规则</label><textarea id="pm-s2-mode-behavior" class="pm-s2-input"></textarea></div><label>视觉风格 Visual Style</label><select id="pm-s2-style" class="pm-s2-input">{_options(cats["visual_styles"], include_custom=True)}</select><div id="pm-s2-style-preview" class="pm-s2-preview pm-s2-style-preview"></div><div id="pm-s2-style-behavior-wrap"><label>自定义视觉风格规则</label><textarea id="pm-s2-style-behavior" class="pm-s2-input"></textarea></div><label>图标体系 Icons</label><select id="pm-s2-icons" class="pm-s2-input">{_options(cats["icons"])}</select><div id="pm-s2-icon-preview" class="pm-s2-preview"></div></div><div><b>配色与字体</b><div class="pm-s2-grid">{palette_fields}</div><label>标题字体</label><select id="pm-s2-heading" class="pm-s2-input">{_options(cats["fonts"])}</select><label>英文标题字体</label><select id="pm-s2-heading-en" class="pm-s2-input">{_options(cats["fonts"])}</select><label>正文字体</label><select id="pm-s2-body" class="pm-s2-input">{_options(cats["fonts"])}</select><label>英文正文字体</label><select id="pm-s2-body-en" class="pm-s2-input">{_options(cats["fonts"])}</select><div class="pm-s2-grid"><div><label>正文 px</label><input id="pm-s2-body-size" type="number" class="pm-s2-input"></div><div><label>标题 px</label><input id="pm-s2-title-size" type="number" class="pm-s2-input"></div><div><label>副标题 px</label><input id="pm-s2-subtitle-size" type="number" class="pm-s2-input"></div><div><label>注释 px</label><input id="pm-s2-annotation-size" type="number" class="pm-s2-input"></div></div></div></div></div>
<div class="pm-s2-card"><b>图片策略</b><div class="pm-s2-grid"><div class="pm-s2-checks">{image_checks}</div><div><label>图片使用说明 Image Notes</label><textarea id="pm-s2-image-notes" class="pm-s2-input">{html.escape(str(defaults["image_notes"]))}</textarea><div id="pm-s2-image-readout" class="pm-s2-preview"></div><div id="pm-s2-ai-wrap"><label>AI 图片路径</label><select id="pm-s2-ai-path" class="pm-s2-input">{_options(cats["image_ai_path"])}</select><label>生成图片风格</label><input id="pm-s2-image-rendering" class="pm-s2-input" value="custom"><label>图片渲染规则</label><textarea id="pm-s2-image-behavior" class="pm-s2-input"></textarea></div></div></div></div>
<div class="pm-s2-card"><b>生产选项</b><div class="pm-s2-checks"><label class="pm-s2-choice"><input id="pm-s2-speaker" type="checkbox"><span>主动生成 / 保留 Speaker Notes</span></label><label class="pm-s2-choice"><input id="pm-s2-animations" type="checkbox"><span>主动进行 Custom Animations</span></label><label class="pm-s2-choice"><input id="pm-s2-narration" type="checkbox"><span>主动生成 Narration Audio</span></label><label class="pm-s2-choice"><input id="pm-s2-refine" type="checkbox"><span>Design Spec 后继续 Review</span></label></div><label>生成模式 Generation Mode</label><select id="pm-s2-generation" class="pm-s2-input">{_options(cats["generation_mode"])}</select><div class="pm-s2-actions"><div id="pm-s2-note" class="pm-s2-muted">确认后生成与官方 validator 兼容的 canonical JSON；当前 host 仍需复制后粘贴回聊天。</div><div style="display:flex;gap:7px;flex-wrap:wrap"><button id="pm-s2-edit" type="button" class="pm-s2-btn hidden">继续编辑</button><button id="pm-s2-confirm" type="button" class="pm-s2-btn primary">确认 Stage 2</button></div></div><div id="pm-s2-capture" class="pm-s2-capture hidden"><b>Captured · not validated</b><textarea id="pm-s2-output" class="pm-s2-input pm-s2-output" readonly></textarea><button id="pm-s2-copy" type="button" class="pm-s2-btn">复制并继续</button><span id="pm-s2-copy-status" class="pm-s2-muted"></span></div></div>
<textarea id="pm-s2-model" class="hidden" aria-hidden="true">{_model_text(model)}</textarea>
<script>
(()=>{{const root=document.getElementById('pm-stage2-parity');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';const q=s=>root.querySelector(s),qa=s=>[...root.querySelectorAll(s)];const M=JSON.parse(q('#pm-s2-model').value);let current=M.selected_direction||0;const palRoles={json.dumps(list(PALETTE_ROLES))};function setSel(id,value){{const el=q(id);if(!el)return;const vals=[...el.options].map(o=>o.value);el.value=vals.includes(String(value))?String(value):(vals.includes('custom')?'custom':(vals[0]||''))}}function pick(o,...keys){{for(const k of keys){{if(o&&typeof o[k]==='string'&&o[k].trim())return o[k]}}return''}}function num(id){{const n=Number(q(id).value);return Number.isFinite(n)&&n>0?n:null}}function setColor(role,value){{q('#pm-s2-color-'+role).value=/^#[0-9a-fA-F]{{6}}$/.test(value||'')?value:'#888888'}}function imageUsage(){{let u=qa('input[name="pm-s2-image-usage"]:checked').map(x=>x.value);if(u.includes('none')&&u.length>1)u=u.filter(x=>x!=='none');return u.length?u:['none']}}function enforceUsage(changed){{const all=qa('input[name="pm-s2-image-usage"]');if(changed.checked&&changed.value==='none')all.forEach(x=>{{if(x!==changed)x.checked=false}});else if(changed.checked){{const none=all.find(x=>x.value==='none');if(none)none.checked=false}}if(!all.some(x=>x.checked)){{const none=all.find(x=>x.value==='none');if(none)none.checked=true}}syncImage()}}function syncImage(){{const u=imageUsage();q('#pm-s2-ai-wrap').classList.toggle('hidden',!u.includes('ai'));const labels=Object.fromEntries(M.catalogs.image_usage.map(x=>[x.id,x.label]));q('#pm-s2-image-readout').textContent='当前允许来源：'+u.map(x=>labels[x]||x).join('、')+(u.includes('none')?'。后续不规划图片资源。':'。来源是允许渠道，不代表每页必须用图。')}}function syncMode(){{const id=q('#pm-s2-mode').value,row=M.catalogs.modes.find(x=>x.id===id);q('#pm-s2-mode-behavior-wrap').classList.toggle('hidden',id!=='custom');q('#pm-s2-mode-preview').innerHTML='<b>'+(id==='custom'?'自定义表达模式':(row?.label||id))+'</b><div>'+(id==='custom'?(q('#pm-s2-mode-behavior').value||'当前方向使用项目专属表达骨架。'):(row?.desc||''))+'</div>'}}function syncStyle(){{const id=q('#pm-s2-style').value,row=M.catalogs.visual_styles.find(x=>x.id===id);q('#pm-s2-style-behavior-wrap').classList.toggle('hidden',id!=='custom');let uri=id==='custom'?M.directions[current].preview_uri:(row?.preview_uri||'');q('#pm-s2-style-preview').innerHTML='<b>'+(id==='custom'?'当前整套自定义方向':(row?.label||id))+'</b>'+(uri?'<img src="'+uri+'" alt="visual style preview">':'')}}function syncIcons(){{const id=q('#pm-s2-icons').value,row=M.catalogs.icons.find(x=>x.id===id),samples=M.icon_preview_data[id]||[];let body='';if(id==='none')body='<div>不使用通用图标。</div>';else if(id==='emoji')body='<div class="pm-s2-icons">📊 💡 ✅ 🧭</div>';else body='<div class="pm-s2-icons">'+samples.map(x=>'<div class="pm-s2-icon">'+x.svg+'<small>'+x.name+'</small></div>').join('')+'</div>';q('#pm-s2-icon-preview').innerHTML='<b>'+(row?.label||id)+'</b><div>'+(row?.desc||'')+'</div>'+body}}function selectDirection(i){{current=i;qa('.pm-s2-dir').forEach((x,j)=>x.classList.toggle('active',i===j));const d=M.directions[i].candidate;setSel('#pm-s2-mode',d.mode||'custom');q('#pm-s2-mode-behavior').value=pick(d,'mode_behavior_zh','mode_behavior_en','mode_behavior');setSel('#pm-s2-style',d.visual_style||'custom');q('#pm-s2-style-behavior').value=pick(d,'visual_style_behavior_zh','visual_style_behavior_en','visual_style_behavior');setSel('#pm-s2-icons',d.icons||'');const p=(d.color||{{}}).palette||{{}};palRoles.forEach(r=>setColor(r,p[r]));const t=d.typography||{{}},h=t.heading||{{}},b=t.body||{{}},sz=t.sizes||{{}},bs=t.body_size||24;setSel('#pm-s2-heading',h.primary||'');setSel('#pm-s2-heading-en',h.english||'');setSel('#pm-s2-body',b.primary||'');setSel('#pm-s2-body-en',b.english||'');q('#pm-s2-body-size').value=bs;q('#pm-s2-title-size').value=sz.title||Math.round(bs*1.75);q('#pm-s2-subtitle-size').value=sz.subtitle||Math.round(bs*1.33);q('#pm-s2-annotation-size').value=sz.annotation||Math.round(bs*.75);const im=d.image_strategy||{{}};q('#pm-s2-image-rendering').value=im.rendering||'custom';q('#pm-s2-image-behavior').value=pick(im,'behavior_zh','behavior_en','behavior');syncMode();syncStyle();syncIcons()}}function init(){{setSel('#pm-s2-delivery',M.defaults.delivery_purpose);setSel('#pm-s2-generation',M.defaults.generation_mode);setSel('#pm-s2-ai-path',M.defaults.image_ai_path);qa('input[name="pm-s2-image-usage"]').forEach(x=>x.checked=M.defaults.image_usage.includes(x.value));q('#pm-s2-speaker').checked=!!M.defaults.proactive_speaker_notes;q('#pm-s2-animations').checked=!!M.defaults.proactive_custom_animations;q('#pm-s2-narration').checked=!!M.defaults.proactive_narration_audio;q('#pm-s2-refine').checked=!!M.defaults.refine_spec;selectDirection(current);syncImage()}}function buildPayload(){{const mode=q('#pm-s2-mode').value,vs=q('#pm-s2-style').value,u=imageUsage();if(mode==='custom'&&!q('#pm-s2-mode-behavior').value.trim())throw new Error('custom mode 需要 behavior');if(vs==='custom'&&!q('#pm-s2-style-behavior').value.trim())throw new Error('custom visual style 需要 behavior');const pal={{}};palRoles.forEach(r=>pal[r]=q('#pm-s2-color-'+r).value.toUpperCase());const values={{stage:'final',page_count:q('#pm-s2-page-count').value,delivery_purpose:q('#pm-s2-delivery').value,mode,visual_style:vs,color:{{name:'static-ui-selection',palette:pal}},icons:q('#pm-s2-icons').value,typography:{{name:'static-ui-selection',heading:{{primary:q('#pm-s2-heading').value,english:q('#pm-s2-heading-en').value,css:'sans-serif'}},body:{{primary:q('#pm-s2-body').value,english:q('#pm-s2-body-en').value,css:'sans-serif'}},body_size:num('#pm-s2-body-size'),body_size_unit:'px',sizes:{{title:num('#pm-s2-title-size'),subtitle:num('#pm-s2-subtitle-size'),annotation:num('#pm-s2-annotation-size')}}}},image_usage:u,image_notes:q('#pm-s2-image-notes').value,proactive_speaker_notes:q('#pm-s2-speaker').checked,proactive_custom_animations:q('#pm-s2-animations').checked,proactive_narration_audio:q('#pm-s2-narration').checked,generation_mode:q('#pm-s2-generation').value,refine_spec:q('#pm-s2-refine').checked}};if(mode==='custom')values.mode_behavior=q('#pm-s2-mode-behavior').value;if(vs==='custom')values.visual_style_behavior=q('#pm-s2-style-behavior').value;if(q('#pm-s2-template-application'))values.template_application=q('#pm-s2-template-application').value;if(u.includes('ai')){{values.image_ai_path=q('#pm-s2-ai-path').value;values.image_strategy={{name:'static-ui-selection',rendering:q('#pm-s2-image-rendering').value,behavior:q('#pm-s2-image-behavior').value}}}}return{{schema:'ppt-master-chat-confirm/v1',surface:'stage2',status:'user-confirmed',recommendation_sha256:M.recommendation_sha256,values}}}}function freeze(on){{qa('input,select,textarea:not(#pm-s2-model):not(#pm-s2-output)').forEach(x=>x.disabled=on);qa('.pm-s2-dir').forEach(x=>x.disabled=on);q('#pm-s2-confirm').classList.toggle('hidden',on);q('#pm-s2-edit').classList.toggle('hidden',!on)}}qa('.pm-s2-dir').forEach((x,i)=>x.addEventListener('click',()=>selectDirection(i)));qa('input[name="pm-s2-image-usage"]').forEach(x=>x.addEventListener('change',()=>enforceUsage(x)));q('#pm-s2-mode').addEventListener('change',syncMode);q('#pm-s2-mode-behavior').addEventListener('input',syncMode);q('#pm-s2-style').addEventListener('change',syncStyle);q('#pm-s2-icons').addEventListener('change',syncIcons);q('#pm-s2-confirm').addEventListener('click',()=>{{try{{const payload=buildPayload(),raw=JSON.stringify(payload,null,2);root.__pptMasterStage2Capture=payload;root.dataset.captureStatus='captured';q('#pm-s2-output').value=raw;q('#pm-s2-capture').classList.remove('hidden');q('#pm-s2-status').textContent='Captured · not validated';q('#pm-s2-status').classList.add('ok');q('#pm-s2-note').textContent='已冻结 canonical JSON。点击“复制并继续”，粘贴到聊天后由 validator 验证。';freeze(true)}}catch(err){{q('#pm-s2-note').textContent=err.message||String(err)}}}});q('#pm-s2-edit').addEventListener('click',()=>{{root.__pptMasterStage2Capture=null;root.dataset.captureStatus='draft';q('#pm-s2-capture').classList.add('hidden');q('#pm-s2-status').textContent='Draft · not validated';q('#pm-s2-status').classList.remove('ok');q('#pm-s2-note').textContent='继续编辑；再次确认会冻结新的 canonical JSON。';freeze(false)}});q('#pm-s2-copy').addEventListener('click',async()=>{{const raw=q('#pm-s2-output').value;try{{await navigator.clipboard.writeText(raw);q('#pm-s2-copy-status').textContent='已复制；粘贴到聊天并发送即可。'}}catch(_e){{q('#pm-s2-output').focus();q('#pm-s2-output').select();document.execCommand?.('copy');q('#pm-s2-copy-status').textContent='已选择/复制；请粘贴到聊天。'}}}});init()}})();
</script>
</div>'''
