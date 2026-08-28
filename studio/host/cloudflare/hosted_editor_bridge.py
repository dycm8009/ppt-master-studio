#!/usr/bin/env python3
"""Runtime bridge between a local PPT Master project and Hosted SVG Editor.

Cloudflare is a remote interaction mirror only.  Every captured edit is replayed
through the pinned Harness' local ``svg_editor/server.py`` API before it is
considered applied to ``svg_output``.

Typical host flow::

    python hosted_editor_bridge.py open <project> \
      --remote-base https://<worker> --harness-commit <40hex>
    python hosted_editor_bridge.py sync <project>
    python hosted_editor_bridge.py apply <project>

The ``open`` command prints the short Hosted Editor URL.  Runtime identity and
capture cursor are stored under ``<project>/live_preview/hosted_editor.json``.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

STATE_NAME = "hosted_editor.json"
LOCK_NAME = "lock.json"
DEFAULT_TIMEOUT = 30
HOST_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


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


def _state_path(project: Path) -> Path:
    return project / "live_preview" / STATE_NAME


def _load_state(project: Path) -> dict[str, Any]:
    path = _state_path(project)
    if not path.exists():
        raise RuntimeError(f"Hosted Editor state missing: {path}; run open first")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Hosted Editor state is invalid")
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


def _skill_dir_from_bridge() -> Path:
    # studio/host/cloudflare/hosted_editor_bridge.py -> repo root
    root = Path(__file__).resolve().parents[3]
    skill_dir = root / "skills" / "ppt-master"
    if not (skill_dir / "scripts" / "svg_editor" / "server.py").is_file():
        raise RuntimeError(f"Pinned ppt-master skill not found from bridge: {skill_dir}")
    return skill_dir


def _local_lock(project: Path) -> dict[str, Any] | None:
    path = project / "live_preview" / LOCK_NAME
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _health(local_base: str) -> dict[str, Any] | None:
    try:
        value = _request_json("GET", local_base.rstrip("/") + "/api/health", timeout=2)
    except RuntimeError:
        return None
    return value if isinstance(value, dict) else None


def ensure_local_harness_server(project: Path, skill_dir: Path | None = None) -> str:
    project = project.resolve()
    lock = _local_lock(project)
    if lock:
        try:
            port = int(lock.get("port", 0))
        except (TypeError, ValueError):
            port = 0
        if port:
            base = f"http://127.0.0.1:{port}"
            health = _health(base)
            if health and health.get("service") == "live_preview":
                return base

    skill = (skill_dir or _skill_dir_from_bridge()).resolve()
    server = skill / "scripts" / "svg_editor" / "server.py"
    command = [
        sys.executable,
        str(server),
        str(project),
        "--live",
        "--daemon",
        "--no-browser",
    ]
    proc = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"official SVG Editor server failed to start: {detail}")

    deadline = time.time() + 10
    while time.time() < deadline:
        lock = _local_lock(project)
        if lock:
            try:
                port = int(lock.get("port", 0))
            except (TypeError, ValueError):
                port = 0
            if port:
                base = f"http://127.0.0.1:{port}"
                health = _health(base)
                if health and health.get("service") == "live_preview":
                    return base
        time.sleep(0.2)
    raise RuntimeError("official SVG Editor server started but no healthy live_preview lock appeared")


def _remote(base: str, path: str) -> str:
    return base.rstrip("/") + path


def _host_headers(host_key: str) -> dict[str, str]:
    return {"X-PPT-Master-Host-Key": host_key}


def create_remote_session(
    remote_base: str,
    session: str,
    host_key: str,
    harness_commit: str,
    *,
    live: bool = True,
) -> dict[str, Any]:
    if len(session) != 48 or any(ch not in "0123456789abcdef" for ch in session):
        raise RuntimeError("session must be 48 lowercase hex characters")
    if len(host_key) != 64 or any(ch not in "0123456789abcdef" for ch in host_key):
        raise RuntimeError("host key must be 64 lowercase hex characters")
    if len(harness_commit) != 40 or any(ch not in "0123456789abcdef" for ch in harness_commit):
        raise RuntimeError("harness commit must be a full 40-hex SHA")
    return _request_json(
        "POST",
        _remote(remote_base, "/api/editor-sessions"),
        {
            "session": session,
            "host_key": host_key,
            "harness_commit": harness_commit,
            "live": live,
        },
    )


def _slide_files(project: Path) -> list[Path]:
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        raise RuntimeError(f"svg_output missing: {svg_dir}")
    return sorted(
        (path for path in svg_dir.iterdir() if path.is_file() and path.suffix.lower() == ".svg"),
        key=lambda p: p.name,
    )


def _asset_files(project: Path):
    for kind in ("images", "assets"):
        root = project / kind
        if not root.is_dir():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            yield kind, root, path


def sync_project(
    project: Path,
    remote_base: str,
    session: str,
    host_key: str,
    *,
    reset_state: bool = False,
    only_slides: set[str] | None = None,
) -> dict[str, Any]:
    headers = _host_headers(host_key)
    slides = []
    for ordinal, path in enumerate(_slide_files(project)):
        if only_slides is not None and path.name not in only_slides:
            continue
        payload = {
            "svg": path.read_text(encoding="utf-8"),
            "mtime": path.stat().st_mtime,
            "ordinal": ordinal,
            "reset_state": reset_state,
        }
        result = _request_json(
            "PUT",
            _remote(remote_base, f"/api/editor-sessions/{session}/slides/{quote(path.name)}"),
            payload,
            headers=headers,
        )
        slides.append(result)

    assets = []
    if only_slides is None:
        for kind, root, path in _asset_files(project):
            rel = path.relative_to(root).as_posix()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            result = _request_json(
                "PUT",
                _remote(remote_base, f"/api/editor-sessions/{session}/asset/{kind}/{quote(rel, safe='/')}"),
                {
                    "content_type": content_type,
                    "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                },
                headers=headers,
            )
            assets.append(result)
    return {"slides": slides, "assets": assets}


def _local_json(local_base: str, method: str, path: str, body: Any | None = None) -> Any:
    return _request_json(method, local_base.rstrip("/") + path, body)


def _clean_remote_edit(edit: dict[str, Any]) -> dict[str, Any]:
    allowed = {"element_id", "text", "attrs", "promote_tspan"}
    return {key: value for key, value in edit.items() if key in allowed}


def replay_capture_to_local(local_base: str, capture: dict[str, Any]) -> list[str]:
    changes = capture.get("changes") or []
    if not isinstance(changes, list):
        raise RuntimeError("Hosted Editor capture changes must be an array")
    touched: set[str] = set()
    for change in changes:
        if not isinstance(change, dict):
            raise RuntimeError("Hosted Editor capture change must be an object")
        slide = str(change.get("slide") or "")
        if not slide:
            raise RuntimeError("Hosted Editor capture change missing slide")
        encoded = quote(slide)
        for edit in change.get("direct_edits") or []:
            _local_json(
                local_base,
                "POST",
                f"/api/slide/{encoded}/edit",
                _clean_remote_edit(dict(edit)),
            )
        for op in change.get("annotation_ops") or []:
            action = str(op.get("action") or "")
            element_id = str(op.get("element_id") or "")
            if action == "set":
                _local_json(
                    local_base,
                    "POST",
                    f"/api/slide/{encoded}/annotate",
                    {"element_id": element_id, "annotation": str(op.get("annotation") or "")},
                )
            elif action == "delete":
                _local_json(
                    local_base,
                    "DELETE",
                    f"/api/slide/{encoded}/annotate/{quote(element_id)}",
                )
            else:
                raise RuntimeError(f"unsupported Hosted Editor annotation action: {action}")
        touched.add(slide)

    if touched:
        saved = _local_json(local_base, "POST", "/api/save-all")
        if saved.get("error"):
            raise RuntimeError(f"official Harness save-all failed: {saved['error']}")
    return sorted(touched)


def pull_and_apply(
    project: Path,
    remote_base: str,
    session: str,
    host_key: str,
    *,
    local_base: str | None = None,
    resync: bool = True,
) -> dict[str, Any]:
    state = _load_state(project)
    cursor = int(state.get("applied_capture_count", 0) or 0)
    response = _request_json(
        "GET",
        _remote(remote_base, f"/api/editor-sessions/{session}/response"),
    )
    captures = response.get("captures") or []
    if not isinstance(captures, list):
        raise RuntimeError("Hosted Editor response captures must be an array")
    if cursor > len(captures):
        raise RuntimeError("local Hosted Editor capture cursor is ahead of remote history")

    local = local_base or ensure_local_harness_server(project)
    touched: set[str] = set()
    for index in range(cursor, len(captures)):
        capture = captures[index]
        if not isinstance(capture, dict):
            raise RuntimeError(f"capture {index} is invalid")
        if capture.get("status") != "captured-not-applied":
            raise RuntimeError(f"capture {index} has unexpected authority status: {capture.get('status')}")
        touched.update(replay_capture_to_local(local, capture))
        state["applied_capture_count"] = index + 1
        state["last_applied_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save_state(project, state)

    session_status = str(response.get("session_status") or "")
    if touched and resync and session_status != "closed":
        sync_project(
            project,
            remote_base,
            session,
            host_key,
            reset_state=False,
            only_slides=touched,
        )

    return {
        "remote_capture_count": len(captures),
        "applied_capture_count": int(state.get("applied_capture_count", 0) or 0),
        "touched_slides": sorted(touched),
        "session_status": session_status,
        "harness_status": "applied-by-local-official-svg-editor" if touched else "no-new-capture",
    }


def open_hosted_editor(
    project: Path,
    remote_base: str,
    harness_commit: str,
    *,
    session: str | None = None,
    host_key: str | None = None,
) -> dict[str, Any]:
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    (project / "svg_output").mkdir(parents=True, exist_ok=True)
    local_base = ensure_local_harness_server(project)
    token = session or secrets.token_hex(24)
    key = host_key or secrets.token_hex(32)
    created = create_remote_session(remote_base, token, key, harness_commit, live=True)
    sync_project(project, remote_base, token, key, reset_state=True)
    state = {
        "schema": "ppt-master-studio-hosted-editor-runtime-state/v1",
        "remote_base": remote_base.rstrip("/"),
        "session": token,
        "host_key": key,
        "harness_commit": harness_commit,
        "local_base": local_base,
        "applied_capture_count": 0,
        "opened_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_state(project, state)
    return {
        "session": token,
        "url": _remote(remote_base, f"/e/{token}"),
        "local_authority": local_base,
        "expires_at": created.get("expires_at"),
    }


def _resolved_state(project: Path, args: argparse.Namespace) -> tuple[str, str, str]:
    state = _load_state(project)
    base = args.remote_base or str(state.get("remote_base") or "")
    session = args.session or str(state.get("session") or "")
    host_key = args.host_key or str(state.get("host_key") or "")
    if not base or not session or not host_key:
        raise RuntimeError("remote base/session/host key missing from args and state")
    return base, session, host_key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PPT Master Cloudflare Hosted SVG Editor runtime bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open", help="start local authority, create Hosted Editor session, and upload current project")
    open_cmd.add_argument("project")
    open_cmd.add_argument("--remote-base", required=True)
    open_cmd.add_argument("--harness-commit", required=True)
    open_cmd.add_argument("--session")
    open_cmd.add_argument("--host-key")

    for name in ("sync", "apply"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project")
        cmd.add_argument("--remote-base")
        cmd.add_argument("--session")
        cmd.add_argument("--host-key")
    sub.choices["sync"].add_argument("--reset-state", action="store_true")
    sub.choices["apply"].add_argument("--local-base")
    sub.choices["apply"].add_argument("--no-resync", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("project")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project).resolve()
    try:
        if args.command == "open":
            result = open_hosted_editor(
                project,
                args.remote_base,
                args.harness_commit,
                session=args.session,
                host_key=args.host_key,
            )
        elif args.command == "sync":
            base, session, host_key = _resolved_state(project, args)
            result = sync_project(project, base, session, host_key, reset_state=args.reset_state)
        elif args.command == "apply":
            base, session, host_key = _resolved_state(project, args)
            result = pull_and_apply(
                project,
                base,
                session,
                host_key,
                local_base=args.local_base,
                resync=not args.no_resync,
            )
        else:
            result = _load_state(project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # host CLI boundary
        print(f"hosted_editor_bridge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
