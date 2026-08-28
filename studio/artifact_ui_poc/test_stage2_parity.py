from __future__ import annotations

import json
import tempfile
from pathlib import Path

from studio.artifact_ui_poc.stage2_parity import (
    stage2_artifact_fragment,
    stage2_artifact_model,
    stage2_default_capture,
)
from studio.static_ui.assets import catalogs
from studio.static_ui.base import PALETTE_ROLES
from studio.static_ui.stage2 import stage2_html
from studio.static_ui.validators import validate_stage2


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def first_id(rows: list[dict], preferred: str | None = None) -> str:
    ids = [str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id")]
    if preferred and preferred in ids:
        return preferred
    if not ids:
        raise AssertionError("catalog unexpectedly empty")
    return ids[0]


def main() -> None:
    cats = catalogs()
    font = first_id(cats.get("fonts", []))
    icon = first_id(cats.get("icons", []))
    delivery = first_id(cats.get("delivery_purpose", []), "balanced")
    generation = first_id(cats.get("generation_mode", []), "continuous")
    ai_path = first_id(cats.get("image_ai_path", []), "auto")

    palette = {
        "background": "#0B0D12",
        "secondary_bg": "#151923",
        "primary": "#E8EAF0",
        "accent": "#8F6CFF",
        "secondary_accent": "#4C8BF5",
        "body_text": "#D7DAE2",
    }
    assert set(palette) == set(PALETTE_ROLES)

    directions = []
    for index in range(3):
        directions.append(
            {
                "label_zh": f"方向 {index + 1}",
                "note_zh": f"完整视觉方向 {index + 1}",
                "mode": "custom",
                "mode_behavior_zh": f"项目专属表达骨架 {index + 1}",
                "visual_style": "custom",
                "visual_style_behavior_zh": f"项目专属视觉规则 {index + 1}",
                "icons": icon,
                "color": {"palette": palette},
                "typography": {
                    "heading": {"primary": font, "english": font},
                    "body": {"primary": font, "english": font},
                    "body_size": 24,
                    "sizes": {"title": 42, "subtitle": 32, "annotation": 18},
                },
                "image_strategy": {
                    "rendering": "custom",
                    "behavior_zh": "只有语义必要时才使用生成图。",
                },
            }
        )

    rec = {
        "stage": "stage2",
        "lang": "zh-CN",
        "page_count": {"value": "91"},
        "image_notes": {"value": "默认 SVG-native；图片不是多样性配额。"},
        "design_directions": {"selected": 1, "candidates": directions},
        "recommend": {
            "delivery_purpose": delivery,
            "generation_mode": generation,
            "image_ai_path": ai_path,
            "image_usage": ["none"],
        },
        "proactive_speaker_notes": {"value": True},
        "proactive_custom_animations": {"value": False},
        "proactive_narration_audio": {"value": False},
        "refine_spec": {"value": True},
    }

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        write_json(project / "confirm_ui" / "recommendations.stage2.json", rec)

        model = stage2_artifact_model(project)
        assert model["schema"] == "ppt-master-chat-inline-stage2-model/v1"
        assert model["selected_direction"] == 1
        assert len(model["directions"]) == 3
        assert model["directions"][1]["label"] == "方向 2"
        assert model["directions"][1]["preview_uri"].startswith("data:image/svg+xml;base64,")
        assert model["authority"]["contract_source"] == "studio.static_ui.validators.validate_stage2"
        assert model["catalogs"]["modes"]
        assert model["catalogs"]["visual_styles"]
        assert model["catalogs"]["icons"]
        assert model["catalogs"]["fonts"]

        # Same recommendation hash as the official Stage 2 Static UI.
        official_html = stage2_html(project)
        assert model["recommendation_sha256"] in official_html

        # The default Artifact capture is accepted by the unchanged official validator.
        capture = stage2_default_capture(model)
        accepted = validate_stage2(project, capture)
        assert accepted["schema"] == "ppt-master-static-ui-accepted/v1"
        assert accepted["surface"] == "stage2"
        assert accepted["status"] == "accepted"
        assert accepted["values"]["stage"] == "final"
        assert accepted["values"]["mode"] == "custom"
        assert accepted["values"]["visual_style"] == "custom"
        assert accepted["values"]["color"]["palette"] == palette

        fragment = stage2_artifact_fragment(model)
        assert "<!doctype" not in fragment.lower()
        assert fragment.count("<script>") == 1
        assert "复制并继续" in fragment
        assert "root.__pptMasterStage2Capture" in fragment
        assert "stage:'final'" in fragment
        assert model["recommendation_sha256"] in fragment
        for required_id in (
            "pm-s2-mode",
            "pm-s2-style",
            "pm-s2-icons",
            "pm-s2-image-notes",
            "pm-s2-generation",
            "pm-s2-speaker",
            "pm-s2-animations",
            "pm-s2-narration",
            "pm-s2-refine",
        ):
            assert required_id in fragment

    print("artifact Stage 2 official parity: PASS")


if __name__ == "__main__":
    main()
