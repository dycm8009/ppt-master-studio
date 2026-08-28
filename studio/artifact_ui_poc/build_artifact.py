from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .adapter import ArtifactHostProfile, plan_artifact_gate
from .copy_handoff import add_copy_and_continue
from .motion_parity import motion_review_artifact_fragment, motion_review_artifact_model
from .project_models import deck_review_artifact_model, stage1_artifact_model
from .renderer import deck_review_artifact_fragment, stage1_artifact_fragment
from .stage2_parity import stage2_artifact_fragment, stage2_artifact_model


ROOT = Path(__file__).resolve().parent
DEFAULT_CAPABILITIES = ROOT / "HOST_CAPABILITIES.json"


def build_artifact_package(
    project: Path,
    surface: str,
    *,
    capabilities_path: Path = DEFAULT_CAPABILITIES,
) -> dict[str, Any]:
    project = project.resolve()
    profile = ArtifactHostProfile.from_capabilities_file(capabilities_path)
    if surface == "stage1":
        model = stage1_artifact_model(project)
        content = stage1_artifact_fragment(model)
        title = "PPT Master · Stage 1"
    elif surface == "stage2":
        model = stage2_artifact_model(project)
        content = stage2_artifact_fragment(model)
        title = "PPT Master · Stage 2"
    elif surface == "deck-review":
        model = deck_review_artifact_model(project)
        content = deck_review_artifact_fragment(model)
        title = "PPT Master · Deck Review"
    elif surface == "motion-review":
        model = motion_review_artifact_model(project)
        content = motion_review_artifact_fragment(model)
        title = "PPT Master · Motion Review"
    else:
        raise ValueError(f"unsupported artifact surface: {surface}")

    content = add_copy_and_continue(content, surface)

    return {
        "schema": "ppt-master-chat-inline-artifact-package/v1",
        "surface": surface,
        "host": "chat-inline-interactive-ui-artifact",
        "render": {
            "language": "html",
            "variant": "inline",
            "icon": "app",
            "title": title,
            "content": content,
        },
        "model": model,
        "gate_plan": plan_artifact_gate(profile, surface),
        "authority": {
            "capture_is_accepted": False,
            "validator": "studio/scripts/static_ui_adapter.py validate",
            "accepted_receipt_required": True,
            "manual_handoff": "copy-paste-canonical-json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a PPT Master chat-inline artifact package")
    parser.add_argument("surface", choices=("stage1", "stage2", "deck-review", "motion-review"))
    parser.add_argument("project", type=Path)
    parser.add_argument("--format", choices=("package", "html", "model"), default="package")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    package = build_artifact_package(args.project, args.surface)
    if args.format == "html":
        output = package["render"]["content"]
    elif args.format == "model":
        output = json.dumps(package["model"], ensure_ascii=False, indent=2) + "\n"
    else:
        output = json.dumps(package, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="" if output.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
