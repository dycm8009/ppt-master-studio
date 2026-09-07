#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("status_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def main() -> int:
    module = load_module(ROOT / "studio/host/cloudflare/interaction_status.py")
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        (project / "confirm_ui").mkdir()
        (project / "live_preview").mkdir()
        (project / "design_spec.md").write_text("# spec", encoding="utf-8")

        empty = module.project_status(project)
        assert empty["surfaces"]["confirm"]["generated"] is False
        assert empty["surfaces"]["confirm"]["access_provided"] is None

        write_json(
            project / "confirm_ui/hosted_browser_handoff.json",
            {
                "schema": "ppt-master-studio-hosted-confirm-browser-state/v1",
                "remote_base": "https://x",
                "session": "a" * 48,
                "harness_commit": "b" * 40,
                "applied_capture_count": 0,
                "transport_mode": "browser-bootstrap-manual-return",
                "feedback_mode": "copy-json",
            },
        )
        confirm = module.project_status(project)["surfaces"]["confirm"]
        assert confirm["launch_ready"] is True and confirm["validated"] is False
        assert confirm["next_action"] == "present-launch-or-apply-copied-json"

        write_json(project / "confirm_ui/result.json", {"stage": "stage1", "status": "stage1-confirmed"})
        write_json(
            project / "confirm_ui/hosted_browser_handoff.json",
            {
                "schema": "ppt-master-studio-hosted-confirm-browser-state/v1",
                "remote_base": "https://x",
                "session": "a" * 48,
                "harness_commit": "b" * 40,
                "applied_capture_count": 1,
                "last_applied_stage": "stage1",
                "transport_mode": "browser-bootstrap-manual-return",
                "feedback_mode": "copy-json",
            },
        )
        confirm = module.project_status(project)["surfaces"]["confirm"]
        assert confirm["user_submitted"] and confirm["validated"] and confirm["applied"]
        assert confirm["next_action"] == "complete-template-handoff"

        write_json(
            project / "live_preview/deck_review_manifest.json",
            {"svg_roster_sha256": "new", "slide_count": 2},
        )
        write_json(
            project / "live_preview/deck_review_receipt.json",
            {"svg_roster_sha256": "old", "result": "approved", "changes_count": 0},
        )
        review = module.project_status(project)["surfaces"]["deck_review"]
        assert review["stale"] is True and review["validated"] is False

    print("interaction status projection: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
