from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from studio.static_ui.assets import animation_registries
from studio.static_ui.base import digest, read_json


MOTION_MODEL_SCHEMA = "ppt-master-chat-inline-motion-review-model/v1"


def motion_review_artifact_model(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan_path = project / "static_ui" / "motion_plan.json"
    plan = read_json(plan_path)
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("static_ui/motion_plan.json must contain non-empty slides[]")

    transitions, object_effects = animation_registries()
    return {
        "schema": MOTION_MODEL_SCHEMA,
        "surface": "motion-review",
        "plan": plan,
        "plan_sha256": digest(plan),
        "transition_effects": transitions,
        "object_effects": object_effects,
        "authority": {
            "capture_schema": "ppt-master-static-motion-review-response/v1",
            "capture_surface": "motion-review",
            "accepted_schema": "ppt-master-static-ui-accepted/v1",
            "validator": "studio/scripts/static_ui_adapter.py validate",
            "contract_source": "studio.static_ui.validators.validate_motion",
            "registry_source": "skills/ppt-master/scripts/pptx_animations.py --list",
        },
    }


def motion_default_capture(model: dict[str, Any]) -> dict[str, Any]:
    if model.get("schema") != MOTION_MODEL_SCHEMA:
        raise ValueError("not a Motion Review chat-inline artifact model")
    decisions = []
    for i, item in enumerate(model["plan"]["slides"]):
        if not isinstance(item, dict):
            continue
        transition = item.get("transition") or {}
        groups = []
        for group in item.get("groups") or []:
            if not isinstance(group, dict):
                continue
            groups.append({
                "id": str(group.get("id", "?")),
                "effect": str(group.get("effect", "none")),
            })
        decisions.append({
            "slide": str(item.get("slide", f"slide-{i+1}")),
            "transition": str(transition.get("effect", "none")),
            "duration": float(transition.get("duration", 0.3)),
            "keep_object_motion": True,
            "groups": groups,
            "comment": "",
            "reason": str(item.get("reason", "")),
        })
    return {
        "schema": "ppt-master-static-motion-review-response/v1",
        "surface": "motion-review",
        "status": "user-confirmed",
        "plan_sha256": model["plan_sha256"],
        "decisions": decisions,
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _model_text(model: dict[str, Any]) -> str:
    return html.escape(json.dumps(model, ensure_ascii=False, separators=(",", ":")), quote=False)


def _options(items: list[str], selected: str) -> str:
    return "".join(
        f'<option value="{_e(item)}" {"selected" if item == selected else ""}>{_e(item)}</option>'
        for item in items
    )


def motion_review_artifact_fragment(model: dict[str, Any]) -> str:
    if model.get("schema") != MOTION_MODEL_SCHEMA:
        raise ValueError("not a Motion Review chat-inline artifact model")
    slides = model["plan"].get("slides") or []
    transitions = model["transition_effects"]
    objects = model["object_effects"]

    rows = []
    for i, slide_plan in enumerate(slides):
        if not isinstance(slide_plan, dict):
            continue
        slide = str(slide_plan.get("slide", f"slide-{i+1}"))
        transition = slide_plan.get("transition") or {}
        effect = str(transition.get("effect", "none"))
        duration = transition.get("duration", 0.3)
        reason = str(slide_plan.get("reason", ""))
        group_rows = []
        for group in slide_plan.get("groups") or []:
            if not isinstance(group, dict):
                continue
            gid = str(group.get("id", "?"))
            geffect = str(group.get("effect", "none"))
            greason = str(group.get("reason", ""))
            group_rows.append(
                f'''<div class="pm-mo-group" data-group="{_e(gid)}"><div><b>{_e(gid)}</b><div class="pm-mo-muted">{_e(greason)}</div></div><select class="pm-mo-input pm-mo-group-effect">{_options(objects, geffect)}</select></div>'''
            )
        groups_html = "".join(group_rows) or '<div class="pm-mo-muted">本页没有计划对象动画。</div>'
        rows.append(
            f'''<section class="pm-mo-card pm-mo-row" data-index="{i}"><div class="pm-mo-row-head"><div><b>{_e(slide)}</b><div class="pm-mo-muted">条件性 Motion Review · 保持克制，不做 deck-wide auto animation</div></div><label class="pm-mo-toggle"><input class="pm-mo-keep" type="checkbox" checked>保留本页对象动画</label></div><div class="pm-mo-grid"><div><label>Transition effect</label><select class="pm-mo-input pm-mo-transition">{_options(transitions, effect)}</select><label>Duration seconds</label><input class="pm-mo-input pm-mo-duration" type="number" min="0.05" step="0.05" value="{_e(duration)}"><label>Reason</label><textarea class="pm-mo-input pm-mo-reason">{html.escape(reason)}</textarea></div><div><label>Object motion</label><div class="pm-mo-groups">{groups_html}</div><label>Override / comment</label><textarea class="pm-mo-input pm-mo-comment" placeholder="例如：只保留 control-loop reveal；其余静态"></textarea></div></div></section>'''
        )

    return f'''<div id="pm-motion-parity" class="pm-mo-root">
<style>
#pm-motion-parity{{width:100%;color:var(--viz-text)}}#pm-motion-parity *{{box-sizing:border-box}}#pm-motion-parity .pm-mo-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;margin-bottom:12px}}#pm-motion-parity .pm-mo-title{{font-weight:750}}#pm-motion-parity .pm-mo-muted{{font-size:11px;color:var(--viz-muted)}}#pm-motion-parity .pm-mo-pill{{font-size:12px;border:1px solid var(--viz-border);border-radius:999px;padding:6px 9px;color:var(--viz-muted)}}#pm-motion-parity .pm-mo-pill.ok{{border-color:var(--viz-accent);background:var(--viz-accent-bg);color:var(--viz-text)}}#pm-motion-parity .pm-mo-card{{border:1px solid var(--viz-border);border-radius:13px;background:var(--viz-card);padding:12px;margin-top:10px}}#pm-motion-parity .pm-mo-row-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}}#pm-motion-parity .pm-mo-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px}}#pm-motion-parity label{{display:block;font-size:12px;font-weight:650;color:var(--viz-muted);margin:8px 0 4px}}#pm-motion-parity .pm-mo-input{{width:100%;min-width:0;border:1px solid var(--viz-border);background:var(--viz-panel);color:var(--viz-text);border-radius:9px;padding:8px 9px;font-size:13px;outline:none}}#pm-motion-parity textarea.pm-mo-input{{min-height:64px;resize:vertical}}#pm-motion-parity .pm-mo-input:focus{{border-color:var(--viz-accent);box-shadow:0 0 0 2px var(--viz-accent-bg)}}#pm-motion-parity .pm-mo-toggle{{display:flex;align-items:center;gap:7px;border:1px solid var(--viz-border);border-radius:9px;padding:7px 9px;background:var(--viz-panel)}}#pm-motion-parity .pm-mo-toggle input{{width:auto;margin:0}}#pm-motion-parity .pm-mo-group{{display:grid;grid-template-columns:minmax(0,1fr) minmax(140px,0.8fr);gap:8px;align-items:center;border-bottom:1px solid var(--viz-border);padding:7px 0}}#pm-motion-parity .pm-mo-actions{{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}}#pm-motion-parity button.pm-mo-btn{{min-height:42px;border-radius:9px;padding:8px 12px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid var(--viz-border);background:var(--viz-card);color:var(--viz-text)}}#pm-motion-parity button.pm-mo-btn.primary{{background:var(--viz-accent);border-color:var(--viz-accent);color:white}}#pm-motion-parity .hidden{{display:none}}@media(max-width:760px){{#pm-motion-parity .pm-mo-grid{{grid-template-columns:1fr}}#pm-motion-parity .pm-mo-group{{grid-template-columns:1fr}}}}
</style>
<div class="pm-mo-head"><div><div class="pm-mo-title">Motion Review · 条件性质量 Gate</div><div class="pm-mo-muted">官方 motion_plan + transition/object animation registry · local capture only</div></div><span id="pm-mo-status" class="pm-mo-pill">Draft · not validated</span></div>
<div id="pm-mo-rows">{"".join(rows)}</div>
<div class="pm-mo-card"><div class="pm-mo-actions"><div id="pm-mo-note" class="pm-mo-muted">默认 transition none；章节边界才使用克制 transition。确认后复制 canonical JSON 回聊天。</div><div style="display:flex;gap:8px;flex-wrap:wrap"><button id="pm-mo-edit" type="button" class="pm-mo-btn hidden">继续编辑</button><button id="pm-mo-confirm" type="button" class="pm-mo-btn primary">确认 Motion Review</button></div></div></div>
<textarea id="pm-motion-model" class="hidden" aria-hidden="true">{_model_text(model)}</textarea>
<script>
(()=>{{const root=document.getElementById('pm-motion-parity');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';const q=s=>root.querySelector(s),qa=s=>[...root.querySelectorAll(s)];const M=JSON.parse(q('#pm-motion-model').value);function build(){{const decisions=qa('.pm-mo-row').map((row,i)=>{{const keep=row.querySelector('.pm-mo-keep').checked;const groups=[...row.querySelectorAll('.pm-mo-group')].map(g=>({{id:g.dataset.group,effect:keep?g.querySelector('.pm-mo-group-effect').value:'none'}}));return{{slide:M.plan.slides[i].slide,transition:row.querySelector('.pm-mo-transition').value,duration:Number(row.querySelector('.pm-mo-duration').value),keep_object_motion:keep,groups,comment:row.querySelector('.pm-mo-comment').value,reason:row.querySelector('.pm-mo-reason').value}}}});for(const d of decisions){{if(!Number.isFinite(d.duration)||d.duration<=0)throw new Error('transition duration 必须为正数')}}return{{schema:'ppt-master-static-motion-review-response/v1',surface:'motion-review',status:'user-confirmed',plan_sha256:M.plan_sha256,decisions}}}}function freeze(on){{qa('input,select,textarea:not(#pm-motion-model)').forEach(x=>x.disabled=on);q('#pm-mo-confirm').classList.toggle('hidden',on);q('#pm-mo-edit').classList.toggle('hidden',!on)}}q('#pm-mo-confirm').addEventListener('click',()=>{{try{{const payload=build();root.__pptMasterMotionReviewCapture=payload;root.dataset.captureStatus='captured';q('#pm-mo-status').textContent='Captured · not validated';q('#pm-mo-status').classList.add('ok');q('#pm-mo-note').textContent='Canonical Motion Review 已冻结。点击“复制并继续”，粘贴到聊天后由 validator 验证。';freeze(true)}}catch(err){{q('#pm-mo-note').textContent=err.message||String(err)}}}});q('#pm-mo-edit').addEventListener('click',()=>{{root.__pptMasterMotionReviewCapture=null;root.dataset.captureStatus='draft';q('#pm-mo-status').textContent='Draft · not validated';q('#pm-mo-status').classList.remove('ok');q('#pm-mo-note').textContent='继续编辑；再次确认会冻结新的 canonical Motion Review。';freeze(false)}})}})();
</script>
</div>'''
