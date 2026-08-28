from __future__ import annotations

import json
import tempfile
from pathlib import Path

from studio.artifact_ui_poc.build_artifact import build_artifact_package
from studio.artifact_ui_poc.motion_parity import (
    motion_default_capture,
    motion_review_artifact_fragment,
    motion_review_artifact_model,
)
from studio.static_ui.validators import validate_motion


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        write_json(
            project / "static_ui" / "motion_plan.json",
            {
                "schema": "ppt-master-motion-plan/v1",
                "slides": [
                    {
                        "slide": "slide-01.svg",
                        "transition": {"effect": "none", "duration": 0.3},
                        "reason": "breathing page remains static",
                        "groups": [
                            {"id": "control-loop", "effect": "none", "reason": "no object motion"},
                        ],
                    },
                    {
                        "slide": "slide-02.svg",
                        "transition": {"effect": "none", "duration": 0.35},
                        "reason": "ordinary content page",
                        "groups": [],
                    },
                ],
            },
        )

        model = motion_review_artifact_model(project)
        assert model["schema"] == "ppt-master-chat-inline-motion-review-model/v1"
        assert model["surface"] == "motion-review"
        assert len(model["transition_effects"]) >= 10
        assert len(model["object_effects"]) >= 50
        assert "none" in model["transition_effects"]
        assert "none" in model["object_effects"]
        assert len(model["plan_sha256"]) == 64

        raw_fragment = motion_review_artifact_fragment(model)
        assert raw_fragment.count("<script") == 1
        assert "ppt-master-static-motion-review-response/v1" in raw_fragment
        assert "__pptMasterMotionReviewCapture" in raw_fragment

        capture = motion_default_capture(model)
        accepted = validate_motion(project, capture)
        assert accepted["schema"] == "ppt-master-static-ui-accepted/v1"
        assert accepted["surface"] == "motion-review"
        assert accepted["status"] == "accepted"
        assert accepted["plan_sha256"] == model["plan_sha256"]
        assert len(accepted["decisions"]) == 2

        package = build_artifact_package(project, "motion-review")
        content = package["render"]["content"]
        assert package["surface"] == "motion-review"
        assert package["model"]["plan_sha256"] == model["plan_sha256"]
        assert "复制并继续" in content
        assert content.count("<script") == 1
        assert package["authority"]["manual_handoff"] == "copy-paste-canonical-json"
        assert package["gate_plan"]["native_handoff"] == "unavailable"

    print("artifact Motion Review official parity: PASS")


if __name__ == "__main__":
    main()
