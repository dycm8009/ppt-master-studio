from .base import *
from .templates import *
from .assets import *
from .review import deck_review_html
def load_response(path: str) -> dict:
    if path == "-": raw=sys.stdin.read()
    else: raw=Path(path).read_text(encoding="utf-8")
    data=json.loads(raw)
    if not isinstance(data,dict): raise ValueError("response must be a JSON object")
    return data


def validate_stage1(project: Path, data: dict) -> dict:
    if data.get("schema")!="ppt-master-chat-confirm/v1" or data.get("surface")!="stage1" or data.get("status")!="user-confirmed": raise ValueError("not a valid stage1 static confirmation")
    rec=read_json(project/"confirm_ui"/"recommendations.stage1.json"); opts,candidates=build_template_options(project)
    if data.get("recommendation_sha256")!=digest(rec): raise ValueError("stage1 recommendation changed after HTML was generated")
    if data.get("options_sha256")!=opts.get("options_sha256"): raise ValueError("template options changed after HTML was generated")
    v=data.get("values");
    if not isinstance(v,dict) or v.get("stage")!="stage1": raise ValueError("stage1 values missing")
    required=("primary_language","canvas","audience","communication_intent","audience_outcome","core_message","delivery_context","artifact_afterlife","content_divergence")
    for k in required:
        if not isinstance(v.get(k),str): raise ValueError(f"stage1 {k} must be a string")
    ts=v.get("template_selection")
    if not isinstance(ts,dict) or ts.get("mode") not in {"free_design","templates"}: raise ValueError("template_selection.mode invalid")
    keys=ts.get("selection_keys")
    if not isinstance(keys,list) or any(not isinstance(k,str) for k in keys): raise ValueError("template_selection.selection_keys invalid")
    if ts["mode"]=="free_design" and keys: raise ValueError("free_design must not select templates")
    if ts["mode"]=="templates" and not keys: raise ValueError("templates mode requires at least one selection")
    resolved=[]; seen_kinds=set()
    for key in keys:
        c=candidates.get(key)
        if not c: raise ValueError(f"unknown template candidate key: {key}")
        if c["kind"] in seen_kinds: raise ValueError(f"template kind selected more than once: {c['kind']}")
        seen_kinds.add(c["kind"])
        item={"source":c["source"],"kind":c["kind"],"workspace_root":c["workspace_root"]}
        if c["source"]=="library": item["id"]=c["id"]
        resolved.append(item)
    return {"schema":"ppt-master-static-ui-accepted/v1","surface":"stage1","status":"accepted","accepted_at":datetime.now(timezone.utc).isoformat(),"values":v,"resolved_template_selections":resolved,"recommendation_sha256":data["recommendation_sha256"],"options_sha256":data["options_sha256"]}


def positive(x: Any) -> bool:
    return isinstance(x,(int,float)) and not isinstance(x,bool) and x>0


def validate_stage2(project: Path, data: dict) -> dict:
    if data.get("schema")!="ppt-master-chat-confirm/v1" or data.get("surface")!="stage2" or data.get("status")!="user-confirmed": raise ValueError("not a valid stage2 static confirmation")
    rec=read_json(project/"confirm_ui"/"recommendations.stage2.json")
    if data.get("recommendation_sha256")!=digest(rec): raise ValueError("stage2 recommendation changed after HTML was generated")
    v=data.get("values")
    if not isinstance(v,dict) or v.get("stage")!="final": raise ValueError("stage2 final values missing")
    for k in ("page_count","delivery_purpose","mode","visual_style","icons","generation_mode"):
        if not isinstance(v.get(k),str) or not v[k].strip(): raise ValueError(f"stage2 {k} must be non-empty")
    if v["generation_mode"] not in {"continuous","split"}: raise ValueError("generation_mode invalid")
    if v["mode"]=="custom" and not str(v.get("mode_behavior","")).strip(): raise ValueError("custom mode requires mode_behavior")
    if v["visual_style"]=="custom" and not str(v.get("visual_style_behavior","")).strip(): raise ValueError("custom visual_style requires visual_style_behavior")
    color=v.get("color") or {}; pal=color.get("palette") or {}
    for r in PALETTE_ROLES:
        if not isinstance(pal.get(r),str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}",pal[r]): raise ValueError(f"palette.{r} must be #RRGGBB")
    typ=v.get("typography") or {}
    for side in ("heading","body"):
        item=typ.get(side) or {}
        for k in ("primary","english","css"):
            if not isinstance(item.get(k),str) or not item[k].strip(): raise ValueError(f"typography.{side}.{k} required")
    if not positive(typ.get("body_size")): raise ValueError("typography.body_size must be positive")
    sizes=typ.get("sizes") or {}
    for k in ("title","subtitle","annotation"):
        if not positive(sizes.get(k)): raise ValueError(f"typography.sizes.{k} must be positive")
    usage=v.get("image_usage")
    if not isinstance(usage,list) or not usage or any(not isinstance(x,str) for x in usage): raise ValueError("image_usage must be a non-empty array")
    if "none" in usage and len(usage)>1: raise ValueError("image_usage none is exclusive")
    if "ai" in usage:
        if v.get("image_ai_path") not in {"auto","api","host-native","manual"}: raise ValueError("image_ai_path invalid")
        im=v.get("image_strategy") or {}
        if not isinstance(im.get("rendering"),str) or not im["rendering"].strip(): raise ValueError("image_strategy.rendering required")
        if im["rendering"]=="custom" and not str(im.get("behavior","")).strip(): raise ValueError("custom image rendering requires behavior")
    for k in ("proactive_speaker_notes","proactive_custom_animations","proactive_narration_audio","refine_spec"):
        if type(v.get(k)) is not bool: raise ValueError(f"{k} must be boolean")
    cumulative = {}
    stage1_path = project / "static_ui" / "accepted.stage1.json"
    if stage1_path.is_file():
        stage1 = read_json(stage1_path)
        stage1_values = stage1.get("values")
        if isinstance(stage1_values, dict):
            cumulative.update({k: val for k, val in stage1_values.items() if k not in {"stage", "template_selection"}})
    cumulative.update(v)
    return {"schema":"ppt-master-static-ui-accepted/v1","surface":"stage2","status":"accepted","accepted_at":datetime.now(timezone.utc).isoformat(),"values":v,"cumulative_values":cumulative,"recommendation_sha256":data["recommendation_sha256"]}


def validate_review(project: Path, data: dict) -> dict:
    if data.get("schema")!="ppt-master-static-deck-review-response/v1" or data.get("surface")!="deck-review": raise ValueError("not a deck-review response")
    current=deck_review_html(project) # rebuilds digest without writing; source of truth
    m=re.search(r'"svg_roster_sha256":\s*"([0-9a-f]{64})"', current)
    if not m: raise ValueError("could not resolve current SVG roster digest")
    if data.get("svg_roster_sha256")!=m.group(1): raise ValueError("SVG roster changed after deck review HTML was generated")
    changes=data.get("changes")
    if not isinstance(changes,list): raise ValueError("deck review changes must be an array")
    known={p.name for p in (project/"svg_output").glob("*.svg")}
    for i,c in enumerate(changes):
        if not isinstance(c,dict) or c.get("slide") not in known or not isinstance(c.get("element_id"),str) or not c["element_id"]: raise ValueError(f"invalid deck review change #{i+1}")
    return {"schema":"ppt-master-static-ui-accepted/v1","surface":"deck-review","status":"accepted","accepted_at":datetime.now(timezone.utc).isoformat(),"changes":changes,"svg_roster_sha256":data["svg_roster_sha256"]}


def validate_motion(project: Path, data: dict) -> dict:
    if data.get("schema") != "ppt-master-static-motion-review-response/v1" or data.get("surface") != "motion-review":
        raise ValueError("not a motion-review response")
    plan = read_json(project / "static_ui" / "motion_plan.json")
    if data.get("plan_sha256") != digest(plan):
        raise ValueError("motion plan changed after HTML was generated")

    transition_effects, object_effects = animation_registries()
    transition_set = set(transition_effects)
    object_set = set(object_effects)
    decisions = data.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("motion decisions must be an array")

    planned = {
        str(item.get("slide")): item
        for item in plan.get("slides", [])
        if isinstance(item, dict)
    }
    for decision in decisions:
        if not isinstance(decision, dict) or str(decision.get("slide")) not in planned:
            raise ValueError("motion decision references unknown slide")
        if decision.get("transition") not in transition_set:
            raise ValueError(f"unsupported transition: {decision.get('transition')}")
        if not isinstance(decision.get("keep_object_motion"), bool):
            raise ValueError("keep_object_motion must be boolean")
        if not positive(decision.get("duration")):
            raise ValueError("motion transition duration must be positive")

        planned_groups = {
            str(group.get("id"))
            for group in (planned[str(decision["slide"])].get("groups") or [])
            if isinstance(group, dict)
        }
        groups = decision.get("groups")
        if not isinstance(groups, list):
            raise ValueError("motion groups must be an array")
        for group in groups:
            if not isinstance(group, dict) or str(group.get("id")) not in planned_groups:
                raise ValueError("motion group references unknown id")
            if group.get("effect") not in object_set:
                raise ValueError(f"unsupported object animation: {group.get('effect')}")

    return {
        "schema": "ppt-master-static-ui-accepted/v1",
        "surface": "motion-review",
        "status": "accepted",
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "decisions": decisions,
        "plan_sha256": data["plan_sha256"],
    }

def validate_response(project: Path, response_path: str) -> Path:
    data=load_response(response_path); surface=data.get("surface")
    if surface=="stage1": accepted=validate_stage1(project,data); name="accepted.stage1.json"
    elif surface=="stage2": accepted=validate_stage2(project,data); name="accepted.stage2.json"
    elif surface=="deck-review": accepted=validate_review(project,data); name="accepted.deck-review.json"
    elif surface=="motion-review": accepted=validate_motion(project,data); name="accepted.motion-review.json"
    else: raise ValueError(f"unsupported response surface: {surface}")
    outdir=project/"static_ui"; outdir.mkdir(parents=True,exist_ok=True); out=outdir/name
    out.write_text(json.dumps(accepted,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return out
