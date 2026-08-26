from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATIC_UI_DIR = Path(__file__).resolve().parent
STUDIO_DIR = STATIC_UI_DIR.parent
REPO_ROOT = STUDIO_DIR.parent
SKILL_DIR = REPO_ROOT / "skills" / "ppt-master"
UPSTREAM_SCRIPT_DIR = SKILL_DIR / "scripts"
CATALOGS_PATH = UPSTREAM_SCRIPT_DIR / "confirm_ui" / "static" / "catalogs.json"
STYLE_PREVIEW_DIR = UPSTREAM_SCRIPT_DIR / "confirm_ui" / "static" / "style_previews"
ICON_LIBRARY_DIR = SKILL_DIR / "templates" / "icons"
ICON_PREVIEW_SAMPLES = {
    "chunk-filled": ("home", "chart-line", "users", "target"),
    "tabler-filled": ("home", "chart-dots", "user", "bulb"),
    "tabler-outline": ("home", "chart-line", "users", "bulb"),
    "phosphor-duotone": ("house", "chart-line", "users", "target"),
}
TEMPLATE_LIBRARY_CONFIG = {
    "brand": ("brands", "brands_index.json"),
    "style": ("styles", "styles_index.json"),
    "layout": ("layouts", "layouts_index.json"),
    "deck": ("decks", "decks_index.json"),
}
PALETTE_ROLES = (
    "background", "secondary_bg", "primary", "accent", "secondary_accent", "body_text"
)

STAGE1_UI = {
    "zh": {
        "primary_language": "主要语言",
        "canvas": "画布尺寸",
        "free_design": "自由设计",
        "free_design_hint": "不安装任何模板工作区，由策略阶段根据已确认的沟通目标自由设计。",
        "use_templates": "使用模板",
        "use_templates_hint": "每种模板类型最多选择一个；版式系统与整套模板可同时选择，版式结构优先。",
        "brand": "品牌", "style": "风格方法", "layout": "版式系统", "deck": "整套模板",
        "specified": "指定工作区", "none": "不选择",
    },
    "en": {
        "primary_language": "Primary language", "canvas": "Canvas",
        "free_design": "Free design", "free_design_hint": "Do not install a template workspace.",
        "use_templates": "Use templates", "use_templates_hint": "Choose at most one per kind; Layout and Deck may coexist, with Layout taking structural precedence.",
        "brand": "Brand", "style": "Style", "layout": "Layout", "deck": "Deck",
        "specified": "Specified workspace", "none": "None",
    },
}

# User-facing names/descriptions for the bundled v5.0.0 template library.
# Canonical ids/keys are never translated and remain the submitted values.
TEMPLATE_LIBRARY_ZH = {
    "brand": {
        "accenture": ("埃森哲", "埃森哲风格的咨询与技术服务视觉体系：黑色基底配紫色强调，适合转型、技术与交付类演示。"),
        "alibaba": ("阿里巴巴", "阿里巴巴风格的商业与云计算视觉体系：黑色基底配标志性橙色，适合平台、商家与云解决方案演示。"),
        "anthropic": ("Anthropic / Claude", "Anthropic / Claude 品牌体系，适合 AI 研究、产品分享、开发者大会、技术培训与发布活动。"),
        "aws": ("AWS", "AWS 风格的云计算视觉体系：深海军蓝配标志性橙色，适合云架构、迁移与 Well-Architected 评审。"),
        "bain": ("贝恩", "贝恩风格的咨询视觉体系：克制的中性色配猩红强调，适合结果导向的战略与绩效演示。"),
        "bcg": ("BCG", "BCG 风格的咨询视觉体系：森林绿与暖中性色，适合增长战略、转型与竞争优势主题。"),
        "deloitte": ("德勤", "德勤风格的专业服务视觉体系：黑色与中性色配标志性绿色，适合审计、税务、风险与咨询。"),
        "google": ("Google", "Google 品牌视觉体系，适合多产品企业演示、开发者活动、教育培训与 Google 生态主题。"),
        "huawei": ("华为", "华为风格的企业视觉体系：近黑与灰色基底配克制红色强调，适合 ICT 解决方案、产品与伙伴主题。"),
        "ibm": ("IBM", "IBM 风格的企业视觉体系：Carbon 蓝与严谨灰阶，适合混合云、AI 与企业咨询演示。"),
        "jpmorgan": ("摩根大通", "摩根大通风格的金融机构视觉体系：企业蓝、海军蓝与中性色，适合研究、银行业务与内部治理。"),
        "mckinsey": ("麦肯锡", "麦肯锡风格的咨询视觉体系：深海军蓝与亮蓝，适合战略、诊断与高管决策演示。"),
        "microsoft": ("微软", "微软风格的企业科技视觉体系：四色产品体系配中性灰，适合 Microsoft 365、Azure 与 IT 项目演示。"),
        "nvidia": ("NVIDIA", "NVIDIA 风格的加速计算视觉体系：近黑基底配标志性绿色，适合 AI、GPU 与数据中心技术演示。"),
        "pwc": ("普华永道", "普华永道风格的专业服务视觉体系：黑色基底配暖橙至玫红色谱，适合鉴证、税务与咨询。"),
        "tencent": ("腾讯", "腾讯风格的互联网与云视觉体系：浅中性色配克制蓝色，适合平台、云与生态主题。"),
        "xiaomi": ("小米", "小米风格的消费科技视觉体系：清爽白色配标志性橙色，适合产品发布、生态与零售演示。"),
    },
    "style": {
        "academic-research": ("学术研究", "从研究问题、方法与结果构建可辩护的论点，同时明确保留局限性。"),
        "consulting-decision": ("咨询决策", "结论先行、证据驱动的决策文档方法，采用克制的分析型设计。"),
        "creative-pitch": ("创意提案", "从真实洞察出发建立一个核心创意，并展示它如何落到所有实际触点。"),
        "incident-postmortem": ("事故复盘", "无责事故复盘方法：重建时间线，区分促成因素与责任归因，并形成可验证的改进行动。"),
        "investor-pitch": ("投资人路演", "以证据而非形容词推动融资叙事，从“为什么是现在”一路回答到“为什么是这支团队”。"),
        "narrative-keynote": ("叙事演讲", "通过张力、转折与具体的人物细节逐步赢得一个核心观点的故事型演讲方法。"),
        "operating-review": ("经营复盘", "周期性经营评审方法：清楚分开结果、偏差、原因与责任人承诺，不弱化不利数字。"),
        "product-launch": ("产品发布", "价值优先的发布方法：每项能力都先由可演示的真实时刻证明，再给出能力名称。"),
        "science-explainer": ("科学解释", "从熟悉经验出发，通过视觉类比建立理解，在提升可理解性的同时不牺牲准确性。"),
        "solution-proposal": ("解决方案提案", "面向客户的方案方法：先证明对问题的理解，再用具体、可计价的计划赢得工作。"),
        "technical-deepdive": ("技术深潜", "机制优先的技术解释方法：每个结论都落到约束、权衡与可观察行为上。"),
        "workshop-teaching": ("工作坊教学", "做中学的培训方法：按目标、示范、练习与真实理解检查的顺序推进。"),
    },
    "layout": {
        "editorial_bleed": ("全幅编辑版式", "纯结构 16:9 系统，包含 10 个 PowerPoint 版式；图片延伸至画布边缘，文字通过遮罩叠放在图片上。"),
        "moments_square": ("方形社交版式", "纯结构 1:1 系统，包含 8 个 PowerPoint 版式，在方形画布上同时使用横向与纵向分区。"),
        "presentation_core": ("通用演示核心", "纯结构 16:9 系统，包含 20 个 PowerPoint 版式，覆盖通用、编辑、图片、流程与数据演示。"),
        "presentation_core_43": ("4:3 通用演示核心", "纯结构 4:3 系统，包含 16 个 PowerPoint 版式，适合投影、课堂、学术与会议室演示。"),
        "report_core": ("报告核心", "纯结构 16:9 系统，包含两个母版和 13 个 PowerPoint 版式，带持续页眉页脚元素与页码占位。"),
        "story_vertical": ("竖屏故事版式", "纯结构 9:16 系统，包含 9 个 PowerPoint 版式，文字区域遵守竖屏故事的顶部与底部安全区。"),
        "xiaohongshu_post": ("小红书图文版式", "纯结构 3:4 竖版系统，包含 10 个 PowerPoint 版式，适合高竖画布上的单栏图文内容。"),
    },
    "deck": {},
}

def stage1_locale(lang: str) -> dict[str, str]:
    return STAGE1_UI["zh"] if str(lang).lower().startswith("zh") else STAGE1_UI["en"]

def template_display(kind: str, candidate: dict, lang: str) -> tuple[str, str]:
    template_id = str(candidate.get("id") or candidate.get("label") or candidate.get("key") or "")
    if str(lang).lower().startswith("zh"):
        row = TEMPLATE_LIBRARY_ZH.get(kind, {}).get(template_id)
        if row: return row
    return str(candidate.get("label") or template_id), str(candidate.get("summary") or "")

def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict): raise ValueError(f"{path} must contain a JSON object")
    return data

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()

def js_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")

def localized(item: dict, lang: str, fallback: str = "") -> str:
    keys = []
    if lang.startswith("zh-TW") or lang.startswith("zh-Hant"): keys += ["label_zh_tw", "name_zh_tw", "note_zh_tw"]
    elif lang.startswith("zh"): keys += ["label_zh", "name_zh", "note_zh"]
    elif lang.startswith("ja"): keys += ["label_ja", "name_ja", "note_ja"]
    else: keys += ["label_en", "name_en", "note_en"]
    keys += ["label", "name", "id"]
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip(): return value.strip()
    return fallback

def value_of(obj: dict, key: str, default: Any = "") -> Any:
    raw = obj.get(key, default)
    if isinstance(raw, dict) and "value" in raw: return raw.get("value")
    return raw
