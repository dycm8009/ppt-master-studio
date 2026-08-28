#!/usr/bin/env python3
"""Network-free Host bridge for the Cloudflare-hosted official Confirm UI.

The helper gzip-compresses the current official Confirm UI snapshot into a URL
fragment. The Cloudflare bootstrap page decodes it in the user's browser,
creates/advances the Durable Object session, then erases the bearer fragment.

When the execution container has no outbound HTTPS, the ChatGPT host can read
the known ``response_url`` with a host-native Web GET, materialize that JSON,
and call ``apply-response``. The captured payload is then replayed through the
pinned official ``confirm_ui/server.py`` Flask `/api/confirm` implementation,
which remains the validation and receipt authority.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any

BOOTSTRAP_PREFIX = "#ppt-master-official-bootstrap-gz="
ADVANCE_PREFIX = "#ppt-master-official-advance-gz="
MAX_JSON_BYTES = 131072
MAX_URL_CHARS = 16000
STATE_NAME = "hosted_browser_handoff.json"
STATE_SCHEMA = "ppt-master-studio-hosted-confirm-browser-state/v1"


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _assert_hex(value: str, length: int, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{label} must be {length} lowercase hex characters")
    return text


def _encode(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"handoff JSON exceeds {MAX_JSON_BYTES} bytes")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def _url(base: str, prefix: str, envelope: dict[str, Any]) -> str:
    result = base.rstrip("/") + "/" + prefix + _encode(envelope)
    if len(result) > MAX_URL_CHARS:
        raise ValueError(
            f"compressed hosted handoff is still too large ({len(result)} chars > {MAX_URL_CHARS}); "
            "use the outbound-HTTPS hosted_confirm_bridge.py path instead"
        )
    return result


def build_bootstrap_url(
    base: str,
    harness_commit: str,
    api_snapshot: dict[str, Any],
    *,
    session: str | None = None,
    host_key: str | None = None,
) -> dict[str, str]:
    token = _assert_hex(session or secrets.token_hex(24), 48, "session")
    key = _assert_hex(host_key or secrets.token_hex(32), 64, "host_key")
    commit = _assert_hex(harness_commit, 40, "harness_commit")
    payload = {
        "schema": "ppt-master-hosted-official-bootstrap/v1",
        "harness_commit": commit,
        "api_snapshot": api_snapshot,
    }
    envelope = {
        "schema": "ppt-master-hosted-official-bootstrap-handoff/v3",
        "session": token,
        "host_key": key,
        "payload": payload,
    }
    return {"session": token, "host_key": key, "url": _url(base, BOOTSTRAP_PREFIX, envelope)}


def build_advance_url(
    base: str,
    session: str,
    host_key: str,
    api_snapshot: dict[str, Any],
) -> dict[str, str]:
    token = _assert_hex(session, 48, "session")
    key = _assert_hex(host_key, 64, "host_key")
    envelope = {
        "schema": "ppt-master-hosted-official-advance-handoff/v2",
        "session": token,
        "host_key": key,
        "api_snapshot": api_snapshot,
    }
    return {"session": token, "host_key": key, "url": _url(base, ADVANCE_PREFIX, envelope)}


def _state_path(project: Path) -> Path:
    return project / "confirm_ui" / STATE_NAME


def _save_state(project: Path, state: dict[str, Any]) -> None:
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load_state(project: Path) -> dict[str, Any]:
    path = _state_path(project)
    if not path.is_file():
        raise RuntimeError(f"Hosted browser handoff state missing: {path}; run bootstrap with --project first")
    state = _load_object(path)
    if state.get("schema") != STATE_SCHEMA:
        raise RuntimeError("unsupported Hosted browser handoff state schema")
    return state


def _persist_bootstrap_state(project: Path, base: str, commit: str, generated: dict[str, str]) -> None:
    _save_state(project, {
        "schema": STATE_SCHEMA,
        "remote_base": base.rstrip("/"),
        "session": generated["session"],
        "host_key": generated["host_key"],
        "harness_commit": _assert_hex(commit, 40, "harness_commit"),
        "applied_capture_count": 0,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


def _official_server_module():
    root = Path(__file__).resolve().parents[3]
    server = root / "skills" / "ppt-master" / "scripts" / "confirm_ui" / "server.py"
    if not server.is_file():
        raise RuntimeError(f"pinned official Confirm UI server missing: {server}")
    spec = importlib.util.spec_from_file_location("ppt_master_pinned_confirm_ui_server", server)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned official Confirm UI server")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _replay_official_confirm(project: Path, remote_stage: str, payload: dict[str, Any]) -> dict[str, Any]:
    official = _official_server_module()
    app = official.create_app(str(project.resolve()), idle_timeout=0)
    with app.test_client() as client:
        response = client.post("/api/confirm", json=payload)
        body = response.get_json(silent=True) or {}
    if response.status_code != 200 or body.get("status") != "ok":
        raise RuntimeError(
            f"pinned official Confirm UI rejected hosted capture: HTTP {response.status_code}: "
            f"{body.get('error', body)}"
        )
    result_file = project / "confirm_ui" / "result.json"
    if not result_file.is_file():
        raise RuntimeError("official Confirm UI accepted capture but result.json is missing")
    result = _load_object(result_file)
    expected = "stage1" if remote_stage == "stage1" else "final"
    if result.get("stage") != expected:
        raise RuntimeError(f"official receipt stage mismatch: expected {expected}, got {result.get('stage')}")
    return result


def apply_response(project: Path, response_data: dict[str, Any], expected_stage: str) -> dict[str, Any]:
    state = _load_state(project)
    if response_data.get("harness_commit") != state.get("harness_commit"):
        raise RuntimeError("Hosted response Harness commit does not match browser handoff state")
    if response_data.get("status") != "captured-not-validated" or response_data.get("harness_status") != "not-validated":
        raise RuntimeError("Hosted response crossed or changed the authority boundary")
    captures = response_data.get("captures")
    if not isinstance(captures, list):
        raise RuntimeError("Hosted response must contain captures[]")
    cursor = int(state.get("applied_capture_count", 0) or 0)
    if cursor >= len(captures):
        raise RuntimeError(f"no new Hosted capture after cursor {cursor}")
    capture = captures[cursor]
    if not isinstance(capture, dict) or capture.get("stage") != expected_stage:
        raise RuntimeError(f"next Hosted capture is not expected stage {expected_stage}")
    payload = capture.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError("Hosted capture payload must be an object")
    result = _replay_official_confirm(project, expected_stage, payload)
    state["applied_capture_count"] = cursor + 1
    state["last_applied_stage"] = expected_stage
    state["last_applied_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_state(project, state)
    return {
        "status": "validated-and-persisted-by-pinned-harness",
        "session": state["session"],
        "stage": expected_stage,
        "result_stage": result.get("stage"),
        "applied_capture_count": state["applied_capture_count"],
    }


def _response_url(base: str, session: str) -> str:
    return f"{base.rstrip('/')}/api/sessions/{session}/response"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PPT Master network-free Cloudflare official Confirm UI bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap")
    boot.add_argument("snapshot", type=Path, help="JSON file containing official api_snapshot")
    boot.add_argument("--base", required=True)
    boot.add_argument("--harness-commit", required=True)
    boot.add_argument("--session")
    boot.add_argument("--host-key")
    boot.add_argument("--project", type=Path)
    advance = sub.add_parser("advance")
    advance.add_argument("snapshot", type=Path, help="JSON file containing Stage-2 official api_snapshot")
    advance.add_argument("--base")
    advance.add_argument("--session")
    advance.add_argument("--host-key")
    advance.add_argument("--project", type=Path)
    apply = sub.add_parser("apply-response")
    apply.add_argument("project", type=Path)
    apply.add_argument("response", type=Path)
    apply.add_argument("--stage", required=True, choices=["stage1", "stage2"])
    status = sub.add_parser("status")
    status.add_argument("project", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "bootstrap":
            snapshot = _load_object(args.snapshot)
            result = build_bootstrap_url(
                args.base,
                args.harness_commit,
                snapshot,
                session=args.session,
                host_key=args.host_key,
            )
            if args.project:
                _persist_bootstrap_state(args.project.resolve(), args.base, args.harness_commit, result)
            result["response_url"] = _response_url(args.base, result["session"])
        elif args.command == "advance":
            snapshot = _load_object(args.snapshot)
            state = _load_state(args.project.resolve()) if args.project else {}
            base = args.base or state.get("remote_base")
            session = args.session or state.get("session")
            host_key = args.host_key or state.get("host_key")
            if not base or not session or not host_key:
                raise RuntimeError("advance requires --project state or explicit --base/--session/--host-key")
            result = build_advance_url(str(base), str(session), str(host_key), snapshot)
            result["response_url"] = _response_url(str(base), result["session"])
        elif args.command == "apply-response":
            result = apply_response(args.project.resolve(), _load_object(args.response), args.stage)
        else:
            result = _load_state(args.project.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"hosted_confirm_handoff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
