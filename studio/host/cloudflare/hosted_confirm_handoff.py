#!/usr/bin/env python3
"""Build compact browser handoffs for the Cloudflare-hosted official Confirm UI.

This helper performs no network I/O.  It gzip-compresses the current official
Confirm UI snapshot into a URL fragment; the Cloudflare bootstrap page decodes
it in the user's browser, creates/advances the Durable Object session, then
removes the bearer fragment before navigating to the short session URL.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
from pathlib import Path
import secrets
import sys
from typing import Any

BOOTSTRAP_PREFIX = "#ppt-master-official-bootstrap-gz="
ADVANCE_PREFIX = "#ppt-master-official-advance-gz="
MAX_JSON_BYTES = 131072
MAX_URL_CHARS = 16000


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
            "use a host-native POST/session staging capability instead"
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build compact Cloudflare official Confirm UI handoff URL")
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap")
    boot.add_argument("snapshot", type=Path, help="JSON file containing official api_snapshot")
    boot.add_argument("--base", required=True)
    boot.add_argument("--harness-commit", required=True)
    boot.add_argument("--session")
    boot.add_argument("--host-key")
    advance = sub.add_parser("advance")
    advance.add_argument("snapshot", type=Path, help="JSON file containing Stage-2 official api_snapshot")
    advance.add_argument("--base", required=True)
    advance.add_argument("--session", required=True)
    advance.add_argument("--host-key", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        snapshot = _load_object(args.snapshot)
        if args.command == "bootstrap":
            result = build_bootstrap_url(
                args.base,
                args.harness_commit,
                snapshot,
                session=args.session,
                host_key=args.host_key,
            )
        else:
            result = build_advance_url(args.base, args.session, args.host_key, snapshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"hosted_confirm_handoff: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
