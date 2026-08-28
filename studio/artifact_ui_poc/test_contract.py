from __future__ import annotations

import json
from pathlib import Path

from studio.artifact_ui_poc.contract import deck_review_capture, handoff_status, stage1_capture


ROOT = Path(__file__).resolve().parent


def main() -> None:
    caps = json.loads((ROOT / "HOST_CAPABILITIES.json").read_text(encoding="utf-8"))
    verified = caps["verified"]
    assert verified["embedded_render"] is True
    assert verified["local_reactive_preview"] is True
    assert verified["artifact_can_submit_payload_to_assistant"] is False
    assert verified["artifact_can_trigger_next_assistant_turn"] is False
    assert caps["authority"]["artifact_confirm_is_accepted"] is False

    values = {
        "stage": "stage1",
        "primary_language": "zh-CN",
        "canvas": "ppt169",
        "audience": "AI Agent 开发者",
        "communication_intent": "技术分享",
        "audience_outcome": "理解 Agent Skills",
        "core_message": "Agent Skills 是可组合、可复用的 Agent 能力协议",
        "delivery_context": "现场分享",
        "artifact_afterlife": "会后参考",
        "content_divergence": "保持事实，允许表达优化",
        "template_selection": {"mode": "free_design", "selection_keys": []},
    }
    stage1 = stage1_capture(
        recommendation_sha256="a" * 64,
        options_sha256="b" * 64,
        values=values,
    )
    assert stage1["schema"] == "ppt-master-chat-confirm/v1"
    assert stage1["surface"] == "stage1"
    assert stage1["status"] == "user-confirmed"
    assert "accepted_at" not in stage1

    deck = deck_review_capture(
        svg_roster_sha256="c" * 64,
        changes=[{"slide": "slide-01.svg", "element_id": "title", "replace_text": "New title"}],
    )
    assert deck["schema"] == "ppt-master-static-deck-review-response/v1"
    assert deck["surface"] == "deck-review"
    assert deck["status"] == "user-confirmed"
    assert deck["changes"][0]["element_id"] == "title"

    bridge = handoff_status()
    assert bridge["transport"] == "unavailable"
    assert bridge["can_submit_to_assistant"] is False
    assert bridge["can_create_accepted_receipt"] is False

    print("chat-inline artifact contract: PASS")


if __name__ == "__main__":
    main()
