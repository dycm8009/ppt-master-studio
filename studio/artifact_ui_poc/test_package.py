from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

from studio.artifact_ui_poc.build_artifact import build_artifact_package


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


def setup_project(project: Path) -> None:
    write_json(
        project / "confirm_ui" / "recommendations.stage1.json",
        {
            "stage": "stage1",
            "primary_language": "zh-CN",
            "audience": "AI Agent 开发者",
            "communication_intent": "技术分享",
            "audience_outcome": "理解 Skills",
            "core_message": "Agent Skills 是可组合能力协议",
            "delivery_context": "现场分享",
            "artifact_afterlife": "会后参考",
            "content_divergence": "保持事实，允许表达优化",
            "recommend": {"canvas": "ppt169"},
        },
    )
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
    (project / "assets").mkdir(parents=True, exist_ok=True)
    (project / "assets" / "tiny.png").write_bytes(PNG_1X1)
    (project / "svg_output").mkdir(parents=True, exist_ok=True)
    (project / "svg_output" / "slide-01.svg").write_text(
        '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
<script>alert(1)</script>
<rect id="hero" onclick="alert(2)" x="0" y="0" width="100" height="100"/>
<image id="photo" href="assets/tiny.png" x="10" y="10" width="20" height="20"/>
</svg>''',
        encoding="utf-8",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        setup_project(project)

        stage = build_artifact_package(project, "stage1")
        assert stage["schema"] == "ppt-master-chat-inline-artifact-package/v1"
        assert stage["surface"] == "stage1"
        assert stage["render"]["variant"] == "inline"
        assert stage["render"]["language"] == "html"
        assert stage["gate_plan"]["artifact_editor"] == "enabled"
        assert stage["gate_plan"]["native_handoff"] == "unavailable"
        assert stage["authority"]["capture_is_accepted"] is False
        assert "AI Agent 开发者" in stage["render"]["content"]

        deck = build_artifact_package(project, "deck-review")
        assert deck["surface"] == "deck-review"
        slide = deck["model"]["slides"][0]
        assert slide["asset_info"]["removed_script_blocks"] == 1
        assert slide["asset_info"]["removed_event_handlers"] == 1
        assert "alert(1)" not in slide["svg"]
        assert "alert(2)" not in slide["svg"]
        assert "data:image/png;base64," in slide["svg"]
        assert deck["model"]["svg_roster_sha256"] in deck["render"]["content"]
        assert deck["gate_plan"]["fallback_required_for_gate_completion"] is True

        (project / "svg_output" / "slide-01.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><image id="remote" href="https://example.com/image.png"/></svg>',
            encoding="utf-8",
        )
        expect_value_error(lambda: build_artifact_package(project, "deck-review"))

    print("host-ready artifact packages: PASS")


if __name__ == "__main__":
    main()
