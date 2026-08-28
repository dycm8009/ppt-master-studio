from __future__ import annotations

from pathlib import Path

from studio.artifact_ui_poc.adapter import ArtifactGateState, ArtifactHostProfile, plan_artifact_gate
from studio.artifact_ui_poc.handoff import delivered_handoff


ROOT = Path(__file__).resolve().parent


def main() -> None:
    profile = ArtifactHostProfile.from_capabilities_file(ROOT / "HOST_CAPABILITIES.json")
    assert profile.realtime_editor_supported() is True
    assert profile.native_handoff_supported() is False

    plan = plan_artifact_gate(profile, "deck-review")
    assert plan["artifact_editor"] == "enabled"
    assert plan["local_capture"] == "enabled"
    assert plan["native_handoff"] == "unavailable"
    assert plan["fallback_required_for_gate_completion"] is True
    assert plan["validator_path"] == "existing-static-ui-validator"

    payload = {
        "schema": "ppt-master-static-deck-review-response/v1",
        "surface": "deck-review",
        "status": "user-confirmed",
        "svg_roster_sha256": "c" * 64,
        "changes": [{"slide": "slide-01.svg", "element_id": "title", "replace_text": "Updated"}],
    }

    state = ArtifactGateState(surface="deck-review")
    assert state.phase == "editing"
    assert state.validator_ready() is False

    state.capture_local(payload)
    assert state.phase == "captured"
    assert state.validator_ready() is False

    receipt = delivered_handoff(
        payload=payload,
        transport="host-native",
        evidence="future-host-test",
    )
    state.mark_delivered(receipt)
    assert state.phase == "delivered"
    assert state.validator_ready() is True

    state.reset_for_editing()
    assert state.phase == "editing"
    assert state.capture is None
    assert state.handoff_receipt is None

    print("artifact Gate adapter: PASS")


if __name__ == "__main__":
    main()
