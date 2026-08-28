from __future__ import annotations

from typing import Any


HEX64 = set("0123456789abcdef")


def _hex64(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in HEX64 for ch in value):
        raise ValueError(f"{name} must be 64 lowercase hex characters")
    return value


def stage1_capture(*, recommendation_sha256: str, options_sha256: str, values: dict[str, Any]) -> dict[str, Any]:
    """Build a captured Stage 1 envelope compatible with the existing validator input contract.

    This function deliberately does not produce an accepted receipt.
    """
    _hex64(recommendation_sha256, "recommendation_sha256")
    _hex64(options_sha256, "options_sha256")
    if not isinstance(values, dict) or values.get("stage") != "stage1":
        raise ValueError("values.stage must be stage1")
    return {
        "schema": "ppt-master-chat-confirm/v1",
        "surface": "stage1",
        "status": "user-confirmed",
        "recommendation_sha256": recommendation_sha256,
        "options_sha256": options_sha256,
        "values": values,
    }


def deck_review_capture(*, svg_roster_sha256: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a captured Deck Review envelope compatible with the existing validator input contract."""
    _hex64(svg_roster_sha256, "svg_roster_sha256")
    if not isinstance(changes, list) or any(not isinstance(item, dict) for item in changes):
        raise ValueError("changes must be a list of objects")
    return {
        "schema": "ppt-master-static-deck-review-response/v1",
        "surface": "deck-review",
        "status": "user-confirmed",
        "svg_roster_sha256": svg_roster_sha256,
        "changes": changes,
    }


def handoff_status() -> dict[str, Any]:
    """Describe the current chat-inline artifact bridge without pretending it exists."""
    return {
        "schema": "ppt-master-artifact-handoff-status/v1",
        "transport": "unavailable",
        "can_submit_to_assistant": False,
        "can_trigger_assistant_turn": False,
        "can_create_accepted_receipt": False,
    }
