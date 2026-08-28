from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

from studio.artifact_ui_poc.project_models import (
    deck_review_artifact_model,
    stage1_artifact_model,
)
from studio.artifact_ui_poc.renderer import (
    deck_review_artifact_fragment,
    stage1_artifact_fragment,
)


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def expect_value_error(fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def build_project(root: Path) -> None:
    write_json(
        root / "confirm_ui" / "recommendations.stage1.json",
        {
            "stage": "stage1",
            "primary_language": "zh-CN",
            "audience": "AI Agent 工程团队",
            "communication_intent": "技术方案评审",
            "audience_outcome": "理解 Skills 交付协议",
            "core_message": "Skills 是 Agent 可组合能力的交付协议",
            "delivery_context": "内部技术分享",
            "artifact_afterlife": "会后工程参考",
            "content_divergence": "保持事实，允许表达优化",
            "recommend": {"canvas": "ppt169"},
        },
    )
    write_json(
        root / "confirm_ui" / "template_options.json",
        {
            "schema_version": 1,
            "phase": "template",
            "default_mode": "free_design",
            "explicit_workspace_roots": [],
            "lang": "zh-CN",
        },
    )
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "tiny.png").write_bytes(PNG_1X1)
    (root / "svg_output").mkdir(parents=True, exist_ok=True)
    (root / "svg_output" / "slide-01.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><text id="title" x="80" y="100">Real title</text><image id="photo" href="assets/tiny.png" x="80" y="140" width="100" height="100"/></svg>',
        encoding="utf-8",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        build_project(project)

        stage_model = stage1_artifact_model(project)
        stage_html = stage1_artifact_fragment(stage_model)
        assert "<!doctype" not in stage_html.lower()
        assert "<html" not in stage_html.lower()
        assert stage_html.count("<script>") == 1
        assert "AI Agent 工程团队" in stage_html
        assert stage_model["recommendation_sha256"] in stage_html
        assert stage_model["options_sha256"] in stage_html
        assert "ppt-master-chat-confirm/v1" in stage_html
        assert "__pptMasterStage1Capture" in stage_html
        assert "Captured · not validated" in stage_html

        deck_model = deck_review_artifact_model(project)
        deck_html = deck_review_artifact_fragment(deck_model)
        assert "<!doctype" not in deck_html.lower()
        assert "<html" not in deck_html.lower()
        assert deck_html.count("<script>") == 1
        assert "data:image/png;base64," in deck_html
        assert deck_model["svg_roster_sha256"] in deck_html
        assert "ppt-master-static-deck-review-response/v1" in deck_html
        assert "__pptMasterDeckReviewCapture" in deck_html
        assert "DOMParser" in deck_html
        assert "撤销" in deck_html and "重做" in deck_html and "重置全部" in deck_html

        (project / "svg_output" / "slide-01.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><image id="missing" href="assets/missing.png"/></svg>',
            encoding="utf-8",
        )
        broken = deck_review_artifact_model(project)
        assert broken["artifact_renderable"] is False
        expect_value_error(lambda: deck_review_artifact_fragment(broken))

    print("real artifact renderer fragments: PASS")


if __name__ == "__main__":
    main()
