from __future__ import annotations

import base64
import json
import re
import tempfile
from pathlib import Path

from studio.artifact_ui_poc.project_models import (
    deck_review_artifact_model,
    stage1_artifact_model,
)
from studio.static_ui.review import deck_review_html
from studio.static_ui.stage1 import stage1_html


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_stage1(project: Path) -> None:
    rec = {
        "stage": "stage1",
        "primary_language": "zh-CN",
        "audience": {"value": "AI Agent 工程团队"},
        "communication_intent": "技术方案评审",
        "audience_outcome": "理解 Skills 交付协议",
        "core_message": "Skills 是 Agent 可组合能力的交付协议",
        "delivery_context": "内部技术分享",
        "artifact_afterlife": "会后工程参考",
        "content_divergence": "保持事实与顺序，允许表达优化",
        "recommend": {"canvas": "ppt169"},
    }
    write_json(project / "confirm_ui" / "recommendations.stage1.json", rec)
    write_json(
        project / "confirm_ui" / "template_options.json",
        {
            "schema_version": 1,
            "phase": "template",
            "default_mode": "free_design",
            "explicit_workspace_roots": [],
            "lang": "zh-CN",
        },
    )

    model = stage1_artifact_model(project)
    assert model["schema"] == "ppt-master-chat-inline-stage1-model/v1"
    assert model["fields"]["audience"] == "AI Agent 工程团队"
    assert model["fields"]["canvas"] == "ppt169"
    assert any(c["id"] == "ppt169" and c["recommended"] for c in model["canvases"])
    assert model["template"]["default_mode"] == "free_design"
    assert model["template"]["library"]["style"]
    assert len(model["recommendation_sha256"]) == 64
    assert len(model["options_sha256"]) == 64

    # The artifact adapter consumes the same source files as the existing Static UI.
    html = stage1_html(project)
    assert model["recommendation_sha256"] in html
    assert model["options_sha256"] in html


def test_deck_review(project: Path) -> None:
    assets = project / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "tiny.png").write_bytes(PNG_1X1)
    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True, exist_ok=True)
    (svg_dir / "slide-01.svg").write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1280 720">
  <rect id="hero" x="0" y="0" width="1280" height="720" fill="#fff"/>
  <text id="title" x="80" y="100">Real project slide</text>
  <image id="photo" href="assets/tiny.png" x="80" y="160" width="100" height="100"/>
</svg>
''',
        encoding="utf-8",
    )
    (svg_dir / "slide-02.svg").write_text(
        '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <text id="subtitle" x="80" y="100">Second slide</text>
</svg>
''',
        encoding="utf-8",
    )

    model = deck_review_artifact_model(project)
    assert model["schema"] == "ppt-master-chat-inline-deck-review-model/v1"
    assert len(model["slides"]) == 2
    assert model["artifact_renderable"] is True
    assert model["issues"] == []
    assert "data:image/png;base64," in model["slides"][0]["svg"]
    assert set(model["slides"][0]["editable_element_ids"]) == {"hero", "title", "photo"}
    assert model["slides"][0]["asset_info"]["embedded_asset_refs"] == 1
    assert model["slides"][0]["asset_info"]["embedded_asset_bytes"] == len(PNG_1X1)

    # Critical: the artifact may inline assets for rendering, but freshness authority
    # must remain byte-for-byte compatible with the existing Deck Review validator.
    static_html = deck_review_html(project)
    match = re.search(r'"svg_roster_sha256":\s*"([0-9a-f]{64})"', static_html)
    assert match, "existing Static UI did not expose a roster digest"
    assert model["svg_roster_sha256"] == match.group(1)


def test_unresolved_asset(project: Path) -> None:
    svg_dir = project / "svg_output"
    for path in svg_dir.glob("*.svg"):
        path.unlink()
    (svg_dir / "slide-missing.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><image id="missing" href="assets/not-found.png"/></svg>',
        encoding="utf-8",
    )
    model = deck_review_artifact_model(project)
    assert model["artifact_renderable"] is False
    assert model["issues"]
    assert "unresolved local asset" in model["issues"][0]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        test_stage1(project)
        test_deck_review(project)
        test_unresolved_asset(project)
    print("artifact real project models: PASS")


if __name__ == "__main__":
    main()
