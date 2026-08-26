from .base import *
from .assets import *
def flatten_visual_styles(cats: dict) -> list[dict]:
    out=[]
    for g in cats.get("visual_styles",[]):
        if isinstance(g,dict): out.extend([x for x in g.get("items",[]) if isinstance(x,dict)])
    return out


def svg_data_uri(svg_text: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode("ascii")


def official_style_preview_uri(style_id: str) -> str:
    path = STYLE_PREVIEW_DIR / f"{style_id}.svg"
    if not path.exists():
        return ""
    return svg_data_uri(path.read_text(encoding="utf-8", errors="replace"))


def icon_preview_samples() -> dict[str, list[dict[str, str]]]:
    """Mirror the official Confirm UI's trusted icon preview sample set."""
    out: dict[str, list[dict[str, str]]] = {}
    for library, names in ICON_PREVIEW_SAMPLES.items():
        rows: list[dict[str, str]] = []
        for name in names:
            path = ICON_LIBRARY_DIR / library / f"{name}.svg"
            if not path.exists():
                continue
            raw = path.read_text(encoding="utf-8", errors="replace")
            raw = re.sub(r"<\?xml[^>]*>\s*", "", raw)
            raw = re.sub(r"<!--.*?-->\s*", "", raw, flags=re.S).strip()
            rows.append({"name": name, "svg": raw})
        out[library] = rows
    return out


def mode_preview_catalog(cats: dict, lang: str) -> list[dict[str, str]]:
    rows=[]
    for item in cats.get("modes", []):
        if not isinstance(item, dict):
            continue
        mode_id=str(item.get("id") or "")
        desc_keys=[]
        if str(lang).lower().startswith("zh-tw") or str(lang).lower().startswith("zh-hant"):
            desc_keys=["desc_zh_tw","desc_zh","desc_en"]
        elif str(lang).lower().startswith("zh"):
            desc_keys=["desc_zh","desc_zh_tw","desc_en"]
        elif str(lang).lower().startswith("ja"):
            desc_keys=["desc_ja","desc_en"]
        else:
            desc_keys=["desc_en","desc_zh"]
        desc=""
        for key in desc_keys:
            value=item.get(key)
            if isinstance(value,str) and value.strip():
                desc=value.strip(); break
        rows.append({"id":mode_id,"label":localized(item,lang,mode_id),"desc":desc})
    return rows


def _hex(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", text) else fallback


def direction_proxy_preview_svg(direction: dict, lang: str) -> str:
    pal = (direction.get("color") or {}).get("palette") or {}
    bg = _hex(pal.get("background"), "#F8FAFC")
    sbg = _hex(pal.get("secondary_bg"), "#EEF2F7")
    pri = _hex(pal.get("primary"), "#183B66")
    acc = _hex(pal.get("accent"), "#F59E0B")
    sacc = _hex(pal.get("secondary_accent"), "#2F8791")
    txt = _hex(pal.get("body_text"), "#172033")
    typ = direction.get("typography") or {}
    head = typ.get("heading") or {}
    body = typ.get("body") or {}
    hfont = html.escape(str(head.get("primary") or head.get("english") or "Arial"), quote=True)
    bfont = html.escape(str(body.get("primary") or body.get("english") or "Arial"), quote=True)
    is_zh = str(lang).lower().startswith("zh")
    kicker = "方案视觉样本" if is_zh else "DESIGN DIRECTION SAMPLE"
    title = "关键判断需要被看见" if is_zh else "Make critical decisions visible"
    sub = "结论、边界与证据形成可追踪的控制链" if is_zh else "A traceable chain of decisions, boundaries and evidence"
    labels = ["判断", "边界", "证据"] if is_zh else ["DECIDE", "BOUND", "PROVE"]
    evidence = "完成证据" if is_zh else "Completion evidence"
    audit = "复核通过" if is_zh else "Review passed"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="{bg}"/>
<rect x="0" y="0" width="18" height="720" fill="{pri}"/>
<text x="72" y="72" font-family="{bfont}" font-size="20" font-weight="700" letter-spacing="3" fill="{sacc}">{kicker}</text>
<text x="72" y="142" font-family="{hfont}" font-size="54" font-weight="700" fill="{pri}">{title}</text>
<text x="72" y="188" font-family="{bfont}" font-size="24" fill="{txt}" opacity=".78">{sub}</text>
<rect x="72" y="238" width="748" height="372" rx="22" fill="{sbg}"/>
<path d="M176 420 H694" stroke="{pri}" stroke-width="5" opacity=".28"/>
<path d="M340 420 l-18 -12 v24 z M530 420 l-18 -12 v24 z" fill="{pri}" opacity=".55"/>
<g font-family="{bfont}" text-anchor="middle">
  <circle cx="180" cy="420" r="76" fill="{bg}" stroke="{pri}" stroke-width="5"/><text x="180" y="408" font-size="18" fill="{sacc}" font-weight="700">01</text><text x="180" y="446" font-size="28" fill="{txt}" font-weight="700">{labels[0]}</text>
  <circle cx="436" cy="420" r="76" fill="{bg}" stroke="{acc}" stroke-width="5"/><text x="436" y="408" font-size="18" fill="{acc}" font-weight="700">02</text><text x="436" y="446" font-size="28" fill="{txt}" font-weight="700">{labels[1]}</text>
  <circle cx="692" cy="420" r="76" fill="{bg}" stroke="{sacc}" stroke-width="5"/><text x="692" y="408" font-size="18" fill="{sacc}" font-weight="700">03</text><text x="692" y="446" font-size="28" fill="{txt}" font-weight="700">{labels[2]}</text>
</g>
<rect x="858" y="238" width="350" height="372" rx="22" fill="{pri}"/>
<text x="900" y="292" font-family="{bfont}" font-size="18" font-weight="700" fill="{bg}" opacity=".7">EVIDENCE</text>
<text x="900" y="370" font-family="{hfont}" font-size="66" font-weight="700" fill="{bg}">3 / 3</text>
<text x="900" y="410" font-family="{bfont}" font-size="24" fill="{bg}" opacity=".92">{evidence}</text>
<rect x="900" y="458" width="252" height="2" fill="{acc}"/>
<circle cx="912" cy="510" r="7" fill="{acc}"/><text x="934" y="518" font-family="{bfont}" font-size="22" fill="{bg}">{audit}</text>
<rect x="72" y="646" width="210" height="10" rx="5" fill="{acc}"/><rect x="294" y="646" width="120" height="10" rx="5" fill="{sacc}"/><rect x="426" y="646" width="72" height="10" rx="5" fill="{pri}" opacity=".4"/>
</svg>'''


def direction_preview_uri(direction: dict, lang: str) -> tuple[str, str]:
    style_id = str(direction.get("visual_style") or "")
    if style_id and style_id != "custom":
        uri = official_style_preview_uri(style_id)
        if uri:
            return uri, ("官方视觉风格 SVG 样本" if str(lang).lower().startswith("zh") else "Official visual-style SVG sample")
    return svg_data_uri(direction_proxy_preview_svg(direction, lang)), ("整套方向代理样本 · 用于比较整体视觉，不代表最终版式" if str(lang).lower().startswith("zh") else "Whole-direction proxy · for visual comparison, not final layout")
