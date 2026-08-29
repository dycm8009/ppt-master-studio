#!/usr/bin/env python3
"""Contract test for direct Cloudflare launch metadata and copied JSON return."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hosted_confirm_bridge as bridge  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize_project(project: Path) -> None:
    confirm = project / "confirm_ui"
    confirm.mkdir(parents=True)
    write_json(confirm / "template_options.json", {
        "schema_version": 1,
        "phase": "template",
        "default_mode": "free_design",
        "lang": "zh",
        "explicit_workspace_roots": [],
    })
    write_json(confirm / "recommendations.stage1.json", {
        "stage": "stage1",
        "lang": "zh",
        "primary_language": "zh-CN",
        "recommend": {"canvas": "ppt169"},
        "audience": {"value": "研发团队"},
        "communication_intent": {"value": "形成决策"},
        "audience_outcome": {"value": "形成共识"},
        "core_message": {"value": "证据驱动"},
        "delivery_context": {"value": "技术分享"},
        "artifact_afterlife": {"value": "评审参考"},
        "content_divergence": {"value": ""},
    })


def stage1_payload() -> dict:
    return {
        "stage": "stage1",
        "primary_language": "zh-CN",
        "canvas": "ppt169",
        "audience": "研发团队",
        "communication_intent": "形成决策",
        "audience_outcome": "形成共识",
        "core_message": "证据驱动",
        "delivery_context": "技术分享",
        "artifact_afterlife": "评审参考",
        "content_divergence": "",
        "template_selection": {"mode": "free_design", "selection_keys": []},
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ppt-master-confirm-return-") as td:
        project = Path(td) / "project"
        initialize_project(project)
        session = "2" * 48
        commit = "1" * 40
        bridge.create_remote_session = lambda *args, **kwargs: {
            "expires_at": "2099-01-01T00:00:00Z"
        }

        opened = bridge.open_hosted_confirm(
            project,
            commit,
            remote_base="https://ppt-master-hosted.example",
            session=session,
            host_key="3" * 64,
        )
        expected_session_url = f"https://ppt-master-hosted.example/s/{session}"
        assert opened["transport_mode"] == "direct-session"
        assert opened["launch_url"] == opened["session_url"] == expected_session_url
        assert opened["url"] == expected_session_url
        assert opened["feedback_mode"] == "auto-pull-with-copy-json-fallback"
        assert opened["response_url"] == (
            f"https://ppt-master-hosted.example/api/sessions/{session}/response"
        )
        assert not (project / ".confirm_ui.lock").exists()

        response = {
            "schema": "ppt-master-hosted-official-captured/v1",
            "status": "captured-not-validated",
            "harness_status": "not-validated",
            "harness_commit": commit,
            "active_stage": "stage1",
            "captures": [{"stage": "stage1", "payload": stage1_payload()}],
            "session_status": "waiting-agent",
        }
        copied_return = {
            "schema": "ppt-master-hosted-confirm-return/v1",
            "session": session,
            "stage": "stage1",
            "response": response,
        }
        applied = bridge.apply_return(project, copied_return)
        assert applied["harness_status"] == "accepted-by-local-official-confirm-ui"
        assert applied["applied_capture_count"] == 1
        result = json.loads(
            (project / "confirm_ui/result.json").read_text(encoding="utf-8")
        )
        assert result["stage"] == "stage1"
        assert result["status"] == "stage1-confirmed"

        wrong_session = dict(copied_return)
        wrong_session["session"] = "f" * 48
        try:
            bridge.apply_return(project, wrong_session)
        except RuntimeError as exc:
            assert "session" in str(exc)
        else:
            raise AssertionError("copied return for a different session was accepted")

    print("direct Cloudflare launch + copied JSON return: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
