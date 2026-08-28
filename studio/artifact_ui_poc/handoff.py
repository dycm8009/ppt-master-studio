from __future__ import annotations

import hashlib
import json
from typing import Any

HANDOFF_SCHEMA = "ppt-master-artifact-handoff/v1"
DELIVERED_TRANSPORTS = {"host-native", "mcp-app", "legacy-static-json"}


def canonical_payload_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unavailable_handoff(reason: str = "chat-inline artifact host exposes no submit-to-assistant bridge") -> dict[str, Any]:
    return {
        "schema": HANDOFF_SCHEMA,
        "status": "unavailable",
        "transport": "unavailable",
        "can_submit_to_assistant": False,
        "can_trigger_assistant_turn": False,
        "can_create_accepted_receipt": False,
        "reason": reason,
    }


def delivered_handoff(*, payload: dict[str, Any], transport: str, evidence: str) -> dict[str, Any]:
    if transport not in DELIVERED_TRANSPORTS:
        raise ValueError(f"unsupported delivered handoff transport: {transport}")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("delivered handoff requires non-empty transport evidence")
    return {
        "schema": HANDOFF_SCHEMA,
        "status": "delivered",
        "transport": transport,
        "payload_sha256": canonical_payload_sha256(payload),
        "evidence": evidence.strip(),
        "can_submit_to_assistant": True,
        "can_create_accepted_receipt": False,
    }


def require_delivered(payload: dict[str, Any], receipt: dict[str, Any]) -> None:
    if not isinstance(receipt, dict):
        raise ValueError("handoff receipt missing")
    if receipt.get("schema") != HANDOFF_SCHEMA or receipt.get("status") != "delivered":
        raise ValueError("artifact capture has not been delivered")
    transport = receipt.get("transport")
    if transport not in DELIVERED_TRANSPORTS:
        raise ValueError("handoff transport is not trusted for delivery")
    expected = canonical_payload_sha256(payload)
    if receipt.get("payload_sha256") != expected:
        raise ValueError("handoff receipt payload digest does not match canonical capture")


def may_invoke_validator(payload: dict[str, Any], receipt: dict[str, Any]) -> bool:
    require_delivered(payload, receipt)
    return True
