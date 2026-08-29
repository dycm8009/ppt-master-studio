#!/usr/bin/env python3
"""Contract test for direct launch, copied return, and session readiness retry."""
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


def _remote_error(status: int, detail: str, *, retryable: bool) -> bridge.RemoteRequestError:
    return bridge.RemoteRequestError(
        f"HTTP {status}: {detail}",
        status=status,
        detail=detail,
        retryable=retryable,
    )


def remote_session_retry_contract() -> None:
    session = "2" * 48
    host_key = "3" * 64
    commit = "1" * 40
    snapshot = {"session": {}, "recommendations": {"stage": "stage1"}}
    original_request = bridge._request_json
    try:
        calls: list[tuple[str, str]] = []
        sleeps: list[float] = []

        def transient_then_success(method, url, body=None, **kwargs):
            calls.append((method, url))
            if len(calls) == 1:
                raise _remote_error(
                    400, "internal error; reference = transient", retryable=True
                )
            if len(calls) == 2:
                raise _remote_error(404, "session missing", retryable=False)
            return {
                "session": session,
                "harness_commit": commit,
                "expires_at": "2099-01-01T00:00:00Z",
            }

        bridge._request_json = transient_then_success
        created = bridge.create_remote_session(
            "https://ppt-master-hosted.example",
            session,
            host_key,
            commit,
            snapshot,
            retry_delays=(0.0,),
            sleep=sleeps.append,
        )
        assert created["session"] == session
        assert [method for method, _url in calls] == ["POST", "GET", "POST"]
        assert sleeps == [0.0]

        calls = []

        def recover_lost_response(method, url, body=None, **kwargs):
            calls.append((method, url))
            if method == "POST":
                raise bridge.RemoteRequestError(
                    "request failed: connection reset",
                    detail="connection reset",
                    retryable=True,
                )
            return {
                "harness_commit": commit,
                "active_stage": "stage1",
                "expires_at": "2099-01-01T00:00:00Z",
            }

        bridge._request_json = recover_lost_response
        recovered = bridge.create_remote_session(
            "https://ppt-master-hosted.example",
            session,
            host_key,
            commit,
            snapshot,
            retry_delays=(),
            sleep=lambda _delay: None,
        )
        assert recovered["recovered_existing_session"] is True
        assert [method for method, _url in calls] == ["POST", "GET"]

        calls = []

        def semantic_failure(method, url, body=None, **kwargs):
            calls.append((method, url))
            raise _remote_error(
                400, "unsupported hosted bootstrap schema", retryable=False
            )

        bridge._request_json = semantic_failure
        try:
            bridge.create_remote_session(
                "https://ppt-master-hosted.example",
                session,
                host_key,
                commit,
                snapshot,
                retry_delays=(0.0,),
                sleep=lambda _delay: None,
            )
        except bridge.RemoteRequestError as exc:
            assert exc.retryable is False
        else:
            raise AssertionError("semantic HTTP 400 was retried or accepted")
        assert len(calls) == 1

        def mismatched_existing_session(method, url, body=None, **kwargs):
            if method == "POST":
                raise _remote_error(409, "session already exists", retryable=False)
            return {
                "harness_commit": "f" * 40,
                "active_stage": "stage1",
            }

        bridge._request_json = mismatched_existing_session
        try:
            bridge.create_remote_session(
                "https://ppt-master-hosted.example",
                session,
                host_key,
                commit,
                snapshot,
                retry_delays=(),
                sleep=lambda _delay: None,
            )
        except RuntimeError as exc:
            assert "different Harness commit" in str(exc)
        else:
            raise AssertionError("mismatched existing session was accepted")
    finally:
        bridge._request_json = original_request


def main() -> int:
    remote_session_retry_contract()
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

    print("direct Cloudflare launch + copied JSON return + readiness retry: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
