from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .handoff import may_invoke_validator, unavailable_handoff


@dataclass(frozen=True)
class ArtifactHostProfile:
    embedded_render: bool
    local_reactive_preview: bool
    artifact_can_submit_payload_to_assistant: bool
    artifact_can_trigger_next_assistant_turn: bool

    @classmethod
    def from_capabilities_file(cls, path: Path) -> "ArtifactHostProfile":
        data = json.loads(path.read_text(encoding="utf-8"))
        verified = data.get("verified") or {}
        return cls(
            embedded_render=bool(verified.get("embedded_render")),
            local_reactive_preview=bool(verified.get("local_reactive_preview")),
            artifact_can_submit_payload_to_assistant=bool(
                verified.get("artifact_can_submit_payload_to_assistant")
            ),
            artifact_can_trigger_next_assistant_turn=bool(
                verified.get("artifact_can_trigger_next_assistant_turn")
            ),
        )

    def realtime_editor_supported(self) -> bool:
        return self.embedded_render and self.local_reactive_preview

    def native_handoff_supported(self) -> bool:
        return (
            self.artifact_can_submit_payload_to_assistant
            and self.artifact_can_trigger_next_assistant_turn
        )


@dataclass
class ArtifactGateState:
    surface: str
    phase: str = "editing"
    capture: dict[str, Any] | None = None
    handoff_receipt: dict[str, Any] | None = None

    def capture_local(self, payload: dict[str, Any]) -> None:
        if self.phase not in {"editing", "captured"}:
            raise ValueError(f"cannot capture while phase={self.phase}")
        if payload.get("surface") != self.surface:
            raise ValueError("capture surface does not match gate state")
        self.capture = payload
        self.handoff_receipt = None
        self.phase = "captured"

    def mark_delivered(self, receipt: dict[str, Any]) -> None:
        if self.phase != "captured" or self.capture is None:
            raise ValueError("a canonical local capture is required before delivery")
        may_invoke_validator(self.capture, receipt)
        self.handoff_receipt = receipt
        self.phase = "delivered"

    def validator_ready(self) -> bool:
        if self.phase != "delivered" or self.capture is None or self.handoff_receipt is None:
            return False
        return may_invoke_validator(self.capture, self.handoff_receipt)

    def reset_for_editing(self) -> None:
        self.capture = None
        self.handoff_receipt = None
        self.phase = "editing"


def plan_artifact_gate(profile: ArtifactHostProfile, surface: str) -> dict[str, Any]:
    realtime = profile.realtime_editor_supported()
    native_handoff = profile.native_handoff_supported()
    return {
        "schema": "ppt-master-artifact-gate-plan/v1",
        "surface": surface,
        "artifact_editor": "enabled" if realtime else "disabled",
        "local_capture": "enabled" if realtime else "disabled",
        "native_handoff": "enabled" if native_handoff else "unavailable",
        "validator_path": "existing-static-ui-validator",
        "fallback_required_for_gate_completion": realtime and not native_handoff,
        "handoff": None if native_handoff else unavailable_handoff(),
    }
