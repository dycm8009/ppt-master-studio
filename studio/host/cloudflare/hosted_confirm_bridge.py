#!/usr/bin/env python3
"""Runtime bridge between the pinned official Confirm API and Cloudflare.

Cloudflare is a remote interaction mirror only.  The pinned official
``confirm_ui/server.py`` remains the validation and receipt authority:

1. invoke the official Confirm API core in-process, without requiring Flask;
2. mirror exact ``/api/session`` + ``/api/recommendations`` state to Cloudflare;
3. let the user interact with the official frontend at a short Hosted URL;
4. pull Hosted captures and replay them unchanged through official ``/api/confirm`` logic;
5. after the agent completes Stage-1 template handoff and writes Stage 2,
   advance the same remote session from exact local official state;
6. when automatic pull is unavailable, accept the page's copied JSON envelope
   through ``apply-return`` without weakening local validation.

An explicit ``--local-base`` still supports a separately running localhost
server for compatibility, but the normal Hosted path is headless and must not
attempt to install or start Flask.

State is stored at ``<project>/confirm_ui/hosted_confirm.json`` with restrictive
permissions when supported.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hosted_confirm_handoff import (
    official_confirm as _headless_confirm,
    official_session as _headless_session,
    official_snapshot as _headless_snapshot,
    unwrap_return_response,
)

STATE_NAME = "hosted_confirm.json"
LOCK_NAME = ".confirm_ui.lock"
DEFAULT_TIMEOUT = 30
DIRECT_TRANSPORT_MODE = "direct-session"
DIRECT_FEEDBACK_MODE = "auto-pull-with-copy-json-fallback"

HOST_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _load_json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def _request_json(
    method: str,
    url: str,
    body: Any | None = None,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": HOST_USER_AGENT,
        **(headers or {}),
    }
    data = None
    if body is not None:
        data = _json_bytes(body)
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"error": raw or exc.reason}
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail.get('error', detail)}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"request failed {url}: {exc}") from exc


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _skill_dir() -> Path:
    skill = _repo_root() / "skills" / "ppt-master"
    server = skill / "scripts" / "confirm_ui" / "server.py"
    if not server.is_file():
        raise RuntimeError(f"Pinned ppt-master Confirm UI server not found: {server}")
    return skill


def _config_file() -> Path:
    return Path(__file__).resolve().with_name("HOSTED_UI.json")


def default_remote_base() -> str:
    path = _config_file()
    if not path.is_file():
        raise RuntimeError("HOSTED_UI.json missing; pass --remote-base explicitly")
    data = json.loads(path.read_text(encoding="utf-8"))
    value = str(data.get("production_base") or "").rstrip("/")
    if not value.startswith("https://"):
        raise RuntimeError("HOSTED_UI.json production_base is invalid")
    return value


def _state_path(project: Path) -> Path:
    return project / "confirm_ui" / STATE_NAME


def _load_state(project: Path) -> dict[str, Any]:
    path = _state_path(project)
    if not path.is_file():
        raise RuntimeError(f"Hosted Confirm state missing: {path}; run open first")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Hosted Confirm state is invalid")
    return value


def _save_state(project: Path, state: dict[str, Any]) -> None:
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _lock(project: Path) -> dict[str, Any] | None:
    path = project / LOCK_NAME
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _local_json(base: str, method: str, path: str, body: Any | None = None) -> Any:
    return _request_json(method, base.rstrip("/") + path, body)


def _healthy_local(base: str, project: Path) -> bool:
    try:
        health = _local_json(base, "GET", "/api/health")
    except RuntimeError:
        return False
    return (
        isinstance(health, dict)
        and health.get("service") == "confirm_ui"
        and str(health.get("project") or "") == str(project.resolve())
    )


def ensure_local_confirm_server(project: Path) -> str:
    project = project.resolve()
    lock = _lock(project)
    if lock:
        try:
            port = int(lock.get("port", 0) or 0)
        except (TypeError, ValueError):
            port = 0
        if port:
            base = f"http://127.0.0.1:{port}"
            if _healthy_local(base, project):
                return base

    server = _skill_dir() / "scripts" / "confirm_ui" / "server.py"
    command = [
        sys.executable,
        str(server),
        str(project),
        "--daemon",
        "--no-browser",
        "--timeout",
        "7200",
    ]
    proc = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"official Confirm UI server failed to start: {detail}")

    deadline = time.time() + 10
    while time.time() < deadline:
        lock = _lock(project)
        if lock:
            try:
                port = int(lock.get("port", 0) or 0)
            except (TypeError, ValueError):
                port = 0
            if port:
                base = f"http://127.0.0.1:{port}"
                if _healthy_local(base, project):
                    return base
        time.sleep(0.2)
    raise RuntimeError("official Confirm UI server started but no healthy lock appeared")


def shutdown_local_confirm_server(project: Path) -> None:
    server = _skill_dir() / "scripts" / "confirm_ui" / "server.py"
    subprocess.run(
        [sys.executable, str(server), str(project.resolve()), "--shutdown"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )


def _remote(base: str, path: str) -> str:
    return base.rstrip("/") + path


def _response_url(base: str, session: str) -> str:
    return _remote(base, f"/api/sessions/{session}/response")


def _host_headers(host_key: str) -> dict[str, str]:
    return {"X-PPT-Master-Host-Key": host_key}


def _snapshot(local_base: str) -> dict[str, Any]:
    session = _local_json(local_base, "GET", "/api/session")
    recommendations = _local_json(local_base, "GET", "/api/recommendations")
    if not isinstance(session, dict) or not isinstance(recommendations, dict):
        raise RuntimeError("official Confirm UI returned invalid snapshot")
    stage = str(recommendations.get("stage") or "")
    if stage not in {"stage1", "stage2"}:
        raise RuntimeError(f"official recommendations stage is not hostable: {stage!r}")
    return {"session": session, "recommendations": recommendations}


def create_remote_session(
    remote_base: str,
    session: str,
    host_key: str,
    harness_commit: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if len(session) != 48 or any(ch not in "0123456789abcdef" for ch in session):
        raise RuntimeError("session must be 48 lowercase hex characters")
    if len(host_key) != 64 or any(ch not in "0123456789abcdef" for ch in host_key):
        raise RuntimeError("host key must be 64 lowercase hex characters")
    if len(harness_commit) != 40 or any(ch not in "0123456789abcdef" for ch in harness_commit):
        raise RuntimeError("harness commit must be a full 40-hex SHA")
    return _request_json(
        "POST",
        _remote(remote_base, "/api/sessions"),
        {
            "session": session,
            "host_key": host_key,
            "payload": {
                "schema": "ppt-master-hosted-official-bootstrap/v1",
                "harness_commit": harness_commit,
                "api_snapshot": snapshot,
            },
        },
    )


def open_hosted_confirm(
    project: Path,
    harness_commit: str,
    *,
    remote_base: str | None = None,
    session: str | None = None,
    host_key: str | None = None,
) -> dict[str, Any]:
    project = project.resolve()
    if not project.is_dir():
        raise RuntimeError(f"project directory missing: {project}")
    base = (remote_base or default_remote_base()).rstrip("/")
    snapshot = _headless_snapshot(project)
    token = session or secrets.token_hex(24)
    key = host_key or secrets.token_hex(32)
    created = create_remote_session(base, token, key, harness_commit, snapshot)
    state = {
        "schema": "ppt-master-studio-hosted-confirm-runtime-state/v1",
        "remote_base": base,
        "session": token,
        "host_key": key,
        "harness_commit": harness_commit,
        "authority_mode": "headless-official-confirm-api",
        "transport_mode": DIRECT_TRANSPORT_MODE,
        "feedback_mode": DIRECT_FEEDBACK_MODE,
        "active_stage": snapshot["recommendations"]["stage"],
        "applied_capture_count": 0,
        "opened_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_state(project, state)
    session_url = _remote(base, f"/s/{token}")
    return {
        "session": token,
        "transport_mode": DIRECT_TRANSPORT_MODE,
        "feedback_mode": DIRECT_FEEDBACK_MODE,
        "launch_url": session_url,
        "session_url": session_url,
        "response_url": _response_url(base, token),
        "url": session_url,
        "active_stage": state["active_stage"],
        "local_authority": "pinned-official-confirm-api:headless",
        "expires_at": created.get("expires_at"),
    }


def _resolved_state(project: Path, args: argparse.Namespace) -> tuple[dict[str, Any], str, str, str]:
    state = _load_state(project)
    base = str(getattr(args, "remote_base", None) or state.get("remote_base") or "").rstrip("/")
    session = str(getattr(args, "session", None) or state.get("session") or "")
    host_key = str(getattr(args, "host_key", None) or state.get("host_key") or "")
    if not base or not session or not host_key:
        raise RuntimeError("remote base/session/host key missing from args and state")
    return state, base, session, host_key


def _apply_response_data(
    project: Path,
    response_data: dict[str, Any],
    *,
    local_base: str | None = None,
) -> dict[str, Any]:
    state = _load_state(project)
    response = unwrap_return_response(
        response_data, expected_session=str(state.get("session") or "")
    )
    if response.get("harness_commit") != state.get("harness_commit"):
        raise RuntimeError("remote Hosted Confirm session is bound to a different Harness commit")
    if response.get("status") != "captured-not-validated" or response.get("harness_status") != "not-validated":
        raise RuntimeError("Hosted response crossed or changed the authority boundary")
    captures = response.get("captures") or []
    if not isinstance(captures, list):
        raise RuntimeError("Hosted Confirm captures must be an array")
    cursor = int(state.get("applied_capture_count", 0) or 0)
    if cursor > len(captures):
        raise RuntimeError("local Hosted Confirm cursor is ahead of remote history")
    authority_mode = "localhost-http" if local_base else "headless-official-confirm-api"
    applied = []
    for index in range(cursor, len(captures)):
        item = captures[index]
        if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
            raise RuntimeError(f"Hosted Confirm capture {index} is invalid")
        stage = str(item.get("stage") or "")
        if stage not in {"stage1", "stage2"}:
            raise RuntimeError(f"Hosted Confirm capture {index} has invalid stage {stage!r}")
        if local_base:
            result = _local_json(local_base, "POST", "/api/confirm", item["payload"])
            if result.get("status") != "ok":
                raise RuntimeError(f"official Confirm UI rejected capture {index}: {result}")
        else:
            _headless_confirm(project, stage, item["payload"])
        applied.append(stage)
        state["applied_capture_count"] = index + 1
        state["last_applied_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state["authority_mode"] = authority_mode
        if local_base:
            state["local_base"] = local_base
        else:
            state.pop("local_base", None)
        _save_state(project, state)
    local_session = (
        _local_json(local_base, "GET", "/api/session")
        if local_base
        else _headless_session(project)
    )
    return {
        "remote_capture_count": len(captures),
        "applied_capture_count": int(state.get("applied_capture_count", 0) or 0),
        "applied_stages": applied,
        "remote_session_status": response.get("session_status"),
        "local_session": local_session,
        "harness_status": "accepted-by-local-official-confirm-ui" if applied else "no-new-capture",
    }


def pull_and_apply(
    project: Path,
    remote_base: str,
    session: str,
    *,
    local_base: str | None = None,
) -> dict[str, Any]:
    response = _request_json("GET", _response_url(remote_base, session))
    return _apply_response_data(project, response, local_base=local_base)


def apply_return(
    project: Path,
    response_data: dict[str, Any],
    *,
    local_base: str | None = None,
) -> dict[str, Any]:
    """Apply JSON copied from the Hosted page without requiring network access."""
    return _apply_response_data(project, response_data, local_base=local_base)

def advance_stage2(
    project: Path,
    remote_base: str,
    session: str,
    host_key: str,
    *,
    local_base: str | None = None,
) -> dict[str, Any]:
    state = _load_state(project)
    snapshot = _snapshot(local_base) if local_base else _headless_snapshot(project)
    if snapshot["recommendations"].get("stage") != "stage2":
        raise RuntimeError("local official Confirm UI is not ready at Stage 2")
    result = _request_json(
        "POST",
        _remote(remote_base, f"/api/sessions/{session}/advance"),
        {"api_snapshot": snapshot},
        headers=_host_headers(host_key),
    )
    state["active_stage"] = "stage2"
    state["authority_mode"] = "localhost-http" if local_base else "headless-official-confirm-api"
    if local_base:
        state["local_base"] = local_base
    else:
        state.pop("local_base", None)
    state["advanced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_state(project, state)
    session_url = _remote(remote_base, f"/s/{session}")
    return {
        "status": result.get("status"),
        "stage": "stage2",
        "transport_mode": DIRECT_TRANSPORT_MODE,
        "feedback_mode": DIRECT_FEEDBACK_MODE,
        "launch_url": session_url,
        "session_url": session_url,
        "response_url": _response_url(remote_base, session),
        "url": session_url,
        "local_session": snapshot["session"],
    }


def close_hosted_confirm(
    project: Path,
    remote_base: str,
    session: str,
    host_key: str,
    *,
    shutdown_local: bool = True,
) -> dict[str, Any]:
    result = _request_json(
        "POST",
        _remote(remote_base, f"/api/sessions/{session}/close"),
        {"reason": "host-complete"},
        headers=_host_headers(host_key),
    )
    if shutdown_local:
        shutdown_local_confirm_server(project)
    return result


def status(project: Path) -> dict[str, Any]:
    state = _load_state(project)
    base = str(state.get("remote_base") or "")
    session = str(state.get("session") or "")
    remote = _request_json("GET", _remote(base, f"/api/sessions/{session}"))
    try:
        local = _headless_session(project)
    except RuntimeError as exc:
        local = {"error": str(exc)}
    return {"state": state, "remote": remote, "local": local}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PPT Master Cloudflare Hosted official Confirm UI runtime bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("project")
    open_cmd.add_argument("--harness-commit", required=True)
    open_cmd.add_argument("--remote-base")
    open_cmd.add_argument("--session")
    open_cmd.add_argument("--host-key")

    for name in ("apply", "advance", "close"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project")
        cmd.add_argument("--remote-base")
        cmd.add_argument("--session")
        cmd.add_argument("--host-key")
    sub.choices["apply"].add_argument("--local-base")
    sub.choices["advance"].add_argument("--local-base")
    sub.choices["close"].add_argument("--keep-local", action="store_true")

    apply_return_cmd = sub.add_parser("apply-return")
    apply_return_cmd.add_argument("project")
    apply_return_cmd.add_argument("response", type=Path)
    apply_return_cmd.add_argument("--local-base")

    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("project")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project).resolve()
    try:
        if args.command == "open":
            result = open_hosted_confirm(
                project,
                args.harness_commit,
                remote_base=args.remote_base,
                session=args.session,
                host_key=args.host_key,
            )
        elif args.command == "apply":
            _state, base, session, _host_key = _resolved_state(project, args)
            result = pull_and_apply(project, base, session, local_base=args.local_base)
        elif args.command == "advance":
            _state, base, session, host_key = _resolved_state(project, args)
            result = advance_stage2(project, base, session, host_key, local_base=args.local_base)
        elif args.command == "apply-return":
            result = apply_return(project, _load_json_file(args.response), local_base=args.local_base)
        elif args.command == "close":
            _state, base, session, host_key = _resolved_state(project, args)
            result = close_hosted_confirm(
                project,
                base,
                session,
                host_key,
                shutdown_local=not args.keep_local,
            )
        else:
            result = status(project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"hosted_confirm_bridge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
