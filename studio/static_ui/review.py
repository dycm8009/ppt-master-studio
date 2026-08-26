from .base import *
from .assets import *
def rewrite_svg_for_static(svg: str) -> str:
    # deck_review.html lives in <project>/static_ui; ordinary project-relative
    # image refs need one ../ prefix. Absolute/data/hash refs remain unchanged.
    def repl(m: re.Match) -> str:
        quote, ref = m.group(1), m.group(2)
        if re.match(r"^(?:data:|https?://|file:|/|#|\.\./)", ref): return m.group(0)
        return f'href={quote}../{ref}{quote}'
    return re.sub(r'href=(["\'])([^"\']+)\1', repl, svg)


def deck_review_html(project: Path) -> str:
    svgs=sorted((project/"svg_output").glob("*.svg"))
    if not svgs: raise ValueError("svg_output/*.svg is required for deck review")
    slides=[]
    for p in svgs:
        raw=rewrite_svg_for_static(p.read_text(encoding="utf-8",errors="replace"))
        raw=re.sub(r"<\?xml[^>]*>\s*", "", raw)
        slides.append({"stem":p.stem,"file":p.name,"svg":raw})
    data={"schema":"ppt-master-static-deck-review/v1","slides":slides,"svg_roster_sha256":digest([(s['file'],hashlib.sha256(s['svg'].encode()).hexdigest()) for s in slides])}
    thumbs=''.join(f'<div class="slide-thumb {"active" if i==0 else ""}" data-i="{i}" onclick="showSlide({i})">{i+1:02d} · {html.escape(s["stem"])}</div>' for i,s in enumerate(slides))
    body=f"""<main class=\"shell\"><header class=\"top\"><h1>Deck Review · 静态视觉检查</h1><p class=\"sub\">点击页面中的对象（优先选择带 id 的最近祖先），可以记录文字替换、SVG 属性修改或需要 AI 判断的注解。这里只生成 Edit Manifest，不直接改源 SVG。</p></header><section class=\"card slide-layout\"><aside class=\"slides\">{thumbs}</aside><div class=\"stage\" id=\"stage\"></div><aside><h3>Selected element</h3><div id=\"sel\" class=\"small\">尚未选择</div><div class=\"field\"><label>Replace text</label><textarea id=\"replace_text\" placeholder=\"留空表示不修改\"></textarea></div><div class=\"field\"><label>Set attribute</label><input id=\"attr_name\" placeholder=\"fill / stroke / opacity / transform ...\"><input id=\"attr_value\" style=\"margin-top:6px\" placeholder=\"new value\"></div><div class=\"field\"><label>AI annotation</label><textarea id=\"annotation\" placeholder=\"例如：这里太拥挤，重排为左流程右证据\"></textarea></div><button class=\"btn\" onclick=\"addChange()\">加入修改清单</button><div id=\"change-count\" class=\"hint\"></div></aside></section><section class=\"card\"><h2>修改清单</h2><div id=\"changes\" class=\"small\"></div></section>{output_card()}</main><div class=\"bar\"><div class=\"inner\"><button class=\"btn\" onclick=\"generateManifest()\">生成 Deck Review JSON</button><span class=\"hint\">回传后由 AI 修改 svg_output，再重新 QA / Export。</span></div></div>"""
    js=r"""
const DATA=JSON.parse(document.getElementById('adapter-data').textContent);let current=0,selectedId='',changes=[];
function showSlide(i){current=i;selectedId='';document.getElementById('sel').textContent='尚未选择';document.querySelectorAll('.slide-thumb').forEach((x,j)=>x.classList.toggle('active',i===j));const st=document.getElementById('stage');st.innerHTML=DATA.slides[i].svg;st.querySelectorAll('[id]').forEach(el=>el.addEventListener('click',ev=>{ev.stopPropagation();selectEl(el)}));}
function selectEl(el){document.querySelectorAll('#stage .selected').forEach(x=>x.classList.remove('selected'));el.classList.add('selected');selectedId=el.id;document.getElementById('sel').textContent=DATA.slides[current].file+' → #'+selectedId;const currentText=(el.children.length===0&&el.textContent||'').trim();document.getElementById('replace_text').value='';document.getElementById('replace_text').placeholder=currentText?('当前：'+currentText):'留空表示不修改';}
function addChange(){if(!selectedId){alert('请先选择一个带 id 的对象');return}const c={slide:DATA.slides[current].file,element_id:selectedId};const txt=document.getElementById('replace_text').value,an=document.getElementById('annotation').value.trim(),n=document.getElementById('attr_name').value.trim(),v=document.getElementById('attr_value').value;if(txt.trim())c.replace_text=txt;if(n)c.set_attribute={name:n,value:v};if(an)c.annotation=an;if(!c.replace_text&&!c.set_attribute&&!c.annotation){alert('没有填写修改内容');return}changes.push(c);document.getElementById('replace_text').value='';document.getElementById('annotation').value='';document.getElementById('attr_name').value='';document.getElementById('attr_value').value='';renderChanges()}
function renderChanges(){document.getElementById('change-count').textContent='已记录 '+changes.length+' 项';document.getElementById('changes').innerHTML=changes.map((c,i)=>'<div class="choice"><span><b>'+c.slide+' · #'+c.element_id+'</b><br>'+escapeHtml(JSON.stringify(c))+'</span><button class="btn secondary" onclick="changes.splice('+i+',1);renderChanges()">删除</button></div>').join('')||'暂无修改'}
function escapeHtml(s){return s.replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
function generateManifest(){putOutput({schema:'ppt-master-static-deck-review-response/v1',surface:'deck-review',status:'user-confirmed',svg_roster_sha256:DATA.svg_roster_sha256,changes})}
showSlide(0);renderChanges();
"""
    return html_doc("PPT Master Static Deck Review",body,data,js)


def motion_review_html(project: Path) -> str:
    plan_path = project / "static_ui" / "motion_plan.json"
    plan = read_json(plan_path)
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("static_ui/motion_plan.json must contain non-empty slides[]")

    transitions, object_effects = animation_registries()
    data = {
        "plan": plan,
        "plan_sha256": digest(plan),
        "transition_effects": transitions,
        "object_effects": object_effects,
    }
    transition_list = "".join(
        f'<option value="{html.escape(effect)}"></option>' for effect in transitions
    )
    object_list = "".join(
        f'<option value="{html.escape(effect)}"></option>' for effect in object_effects
    )

    blocks = []
    for i, slide_plan in enumerate(slides):
        slide = str(slide_plan.get("slide", f"slide-{i+1}"))
        transition = slide_plan.get("transition") or {}
        effect = str(transition.get("effect", "none"))
        duration = transition.get("duration", 0.3)
        reason = str(slide_plan.get("reason", ""))
        groups = slide_plan.get("groups") or []

        group_rows = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            gid = str(group.get("id", "?"))
            group_effect = str(group.get("effect", "none"))
            group_reason = str(group.get("reason", ""))
            group_rows.append(
                f'<div class="choice group-row" data-group="{html.escape(gid)}">'
                f'<div style="flex:1"><b>{html.escape(gid)}</b>'
                f'<div class="hint">{html.escape(group_reason)}</div>'
                f'<input class="group-effect" list="object-effects" '
                f'value="{html.escape(group_effect)}" style="margin-top:6px"></div></div>'
            )
        groups_html = "".join(group_rows) or '<div class="hint">本页没有计划对象动画。</div>'

        blocks.append(
            f'<section class="card motion-row" data-i="{i}">'
            f'<h3>{html.escape(slide)}</h3><div class="grid"><div>'
            f'<div class="field"><label>Transition effect</label>'
            f'<input class="tr" list="transition-effects" value="{html.escape(effect)}"></div>'
            f'<div class="field"><label>Duration seconds</label>'
            f'<input class="dur" type="number" step="0.05" value="{html.escape(str(duration))}"></div>'
            f'<div class="field"><label>Reason</label>'
            f'<textarea class="reason">{html.escape(reason)}</textarea></div></div>'
            f'<div><label>Object motion</label>{groups_html}'
            f'<label class="choice"><input class="keep-groups" type="checkbox" checked>'
            f'<span>启用本页对象动画；取消则本页对象动画全部设为 none</span></label>'
            f'<div class="field"><label>Override / comment</label>'
            f'<textarea class="comment" placeholder="例如：只保留 control-loop 的 reveal；其余静态"></textarea>'
            f'</div></div></div></section>'
        )

    body = (
        '<main class="shell"><header class="top">'
        '<h1>Motion Review · 条件性质量 Gate</h1>'
        '<p class="sub">这是 PPT Master Studio Adapter 扩展，不是官方 Confirm UI。'
        '输入框使用官方当前 transition / object-animation registry，可保留或改成任意受支持的原生效果。</p>'
        f'</header><datalist id="transition-effects">{transition_list}</datalist>'
        f'<datalist id="object-effects">{object_list}</datalist>{"".join(blocks)}'
        f'{output_card()}</main><div class="bar"><div class="inner">'
        '<button class="btn" onclick="generateMotion()">确认 Motion Plan</button></div></div>'
    )
    js = r"""
const DATA=JSON.parse(document.getElementById('adapter-data').textContent);
function generateMotion(){
  const decisions=[...document.querySelectorAll('.motion-row')].map((r,i)=>{
    const enabled=r.querySelector('.keep-groups').checked;
    const groups=[...r.querySelectorAll('.group-row')].map(g=>({
      id:g.dataset.group,
      effect:enabled?g.querySelector('.group-effect').value:'none'
    }));
    return {
      slide:DATA.plan.slides[i].slide,
      transition:r.querySelector('.tr').value,
      duration:Number(r.querySelector('.dur').value),
      keep_object_motion:enabled,
      groups,
      comment:r.querySelector('.comment').value,
      reason:r.querySelector('.reason').value
    };
  });
  putOutput({schema:'ppt-master-static-motion-review-response/v1',surface:'motion-review',status:'user-confirmed',plan_sha256:DATA.plan_sha256,decisions});
}
"""
    return html_doc("PPT Master Static Motion Review", body, data, js)
