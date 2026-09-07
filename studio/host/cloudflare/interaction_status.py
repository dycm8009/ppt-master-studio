#!/usr/bin/env python3
"""Project-local interaction status projection for PPT Master Studio.

This helper never owns a workflow decision.  It projects evidence already
written by the pinned Harness and Studio transport adapters into one small,
explicit state model so a host cannot accidentally describe a remote capture as
validated/applied or a generated file as already presented to the user.

`access_provided` is intentionally always null here.  Only the host that actually
renders a hyperlink/file card can truthfully set that user-visible fact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_SCHEMA = "ppt-master-project-interaction-state/v1"
SURFACE_SCHEMA = "ppt-master-interaction-surface-state/v1"


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _surface(
    name: str,
    *,
    generated: bool = False,
    launch_ready: bool = False,
    user_submitted: bool = False,
    validated: bool = False,
    applied: bool = False,
    stale: bool = False,
    authority: str,
    next_action: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SURFACE_SCHEMA,
        "surface": name,
        "generated": bool(generated),
        "launch_ready": bool(launch_ready),
        # Host-owned fact: this helper cannot know whether the UI/file was
        # actually rendered in the user's client.
        "access_provided": None,
        "user_submitted": bool(user_submitted),
        "validated": bool(validated),
        "applied": bool(applied),
        "stale": bool(stale),
        "authority": authority,
        "next_action": next_action,
        "details": details or {},
    }


def confirm_state(project: Path) -> dict[str, Any]:
    confirm = project / "confirm_ui"
    direct = _load_object(confirm / "hosted_confirm.json")
    browser = _load_object(confirm / "hosted_browser_handoff.json")
    state = direct or browser
    result = _load_object(confirm / "result.json")
    handoff = _load_object(confirm / "template_handoff.json")

    if not state:
        return _surface(
            "confirm",
            authority="pinned-official-confirm-api",
            next_action="open-confirm-surface",
        )

    mode = "direct" if direct else "browser-manual-return"
    active_stage = str(state.get("active_stage") or state.get("last_applied_stage") or "stage1")
    applied_count = int(state.get("applied_capture_count", 0) or 0)
    user_submitted = applied_count > 0

    result_stage = str((result or {}).get("stage") or "")
    result_status = str((result or {}).get("status") or "")
    stage1_valid = result_stage == "stage1" and result_status == "stage1-confirmed"
    final_valid = result_stage == "final" and result_status == "confirmed"
    validated = final_valid or (active_stage == "stage1" and stage1_valid)
    applied = validated

    if final_valid:
        next_action = "continue-after-final-confirmation"
    elif stage1_valid:
        if handoff and handoff.get("status") == "ready":
            next_action = "author-or-present-stage2"
        else:
            next_action = "complete-template-handoff"
    elif mode == "browser-manual-return":
        next_action = "present-launch-or-apply-copied-json"
    else:
        next_action = "present-launch-or-pull-and-apply"

    details = {
        "transport_mode": state.get("transport_mode"),
        "feedback_mode": state.get("feedback_mode"),
        "active_stage": active_stage,
        "applied_capture_count": applied_count,
        "result_stage": result_stage or None,
        "result_status": result_status or None,
        "harness_commit": state.get("harness_commit"),
    }
    return _surface(
        "confirm",
        generated=True,
        launch_ready=bool(state.get("session") and state.get("remote_base")),
        user_submitted=user_submitted,
        validated=validated,
        applied=applied,
        authority="pinned-official-confirm-api",
        next_action=next_action,
        details=details,
    )


def editor_state(project: Path) -> dict[str, Any]:
    state = _load_object(project / "live_preview" / "hosted_editor.json")
    if not state:
        return _surface(
            "svg-editor",
            authority="pinned-official-svg-editor",
            next_action="open-editor-if-route-requires-it",
        )
    applied_count = int(state.get("applied_capture_count", 0) or 0)
    details = {
        "session": state.get("session"),
        "harness_commit": state.get("harness_commit"),
        "applied_capture_count": applied_count,
        "last_applied_at": state.get("last_applied_at"),
    }
    return _surface(
        "svg-editor",
        generated=True,
        launch_ready=bool(state.get("session") and state.get("remote_base")),
        user_submitted=applied_count > 0,
        validated=applied_count > 0,
        applied=applied_count > 0,
        authority="pinned-official-svg-editor",
        next_action="continue-generation-or-apply-new-editor-captures",
        details=details,
    )


def deck_review_state(project: Path) -> dict[str, Any]:
    runtime = project / "live_preview"
    manifest = _load_object(runtime / "deck_review_manifest.json")
    response = _load_object(runtime / "deck_review_response.json")
    receipt = _load_object(runtime / "deck_review_receipt.json")
    html_path = runtime / "deck_review.html"
    if not manifest:
        return _surface(
            "deck-review",
            authority="pinned-deck-review-handoff",
            next_action="build-deck-review-after-final-svg-quality-pass",
        )

    roster_hash = str(manifest.get("svg_roster_sha256") or "")
    receipt_hash = str((receipt or {}).get("svg_roster_sha256") or "")
    response_hash = str((response or {}).get("svg_roster_sha256") or "")
    current_receipt = bool(receipt and receipt_hash == roster_hash)
    current_response = bool(response and response_hash == roster_hash)
    stale = bool(receipt and receipt_hash and receipt_hash != roster_hash)
    result = str((receipt or {}).get("result") or "") if current_receipt else ""

    if result == "approved" and int((receipt or {}).get("changes_count", 0) or 0) == 0:
        next_action = "continue-to-export"
    elif result == "changes-requested":
        next_action = "apply-requested-changes-and-rebuild-review"
    else:
        next_action = "present-review-html-and-apply-user-response"

    details = {
        "svg_roster_sha256": roster_hash,
        "slide_count": manifest.get("slide_count"),
        "changed_slide_count": manifest.get("changed_slide_count"),
        "previous_review": manifest.get("previous_review"),
        "receipt_result": result or None,
    }
    return _surface(
        "deck-review",
        generated=True,
        launch_ready=html_path.is_file(),
        user_submitted=current_response,
        validated=current_receipt,
        applied=current_receipt,
        stale=stale,
        authority="pinned-deck-review-handoff",
        next_action=next_action,
        details=details,
    )


def storyboard_state(project: Path) -> dict[str, Any]:
    runtime = project / "live_preview"
    manifest = _load_object(runtime / "storyboard.json")
    html_path = runtime / "storyboard.html"
    spec = project / "design_spec.md"
    if not manifest:
        return _surface(
            "storyboard",
            authority="design-spec-read-only-projection",
            next_action="build-after-design-spec-is-valid",
        )

    stale = False
    if spec.is_file():
        import hashlib

        current = hashlib.sha256(spec.read_bytes()).hexdigest()
        stale = current != str(manifest.get("design_spec_sha256") or "")
    return _surface(
        "storyboard",
        generated=True,
        launch_ready=html_path.is_file(),
        stale=stale,
        authority="design-spec-read-only-projection",
        next_action="rebuild-storyboard" if stale else "optional-read-only-review",
        details={
            "design_spec_sha256": manifest.get("design_spec_sha256"),
            "slide_count": manifest.get("slide_count"),
            "risk_counts": manifest.get("risk_counts"),
        },
    )


def project_status(project: Path) -> dict[str, Any]:
    project = project.resolve()
    return {
        "schema": PROJECT_SCHEMA,
        "project": str(project),
        "host_claim_boundary": {
            "access_provided": "Only the host/client that actually renders a link or file may set this to true.",
            "pending_remote_capture": "Project-local files cannot prove a remote capture that has not yet been pulled/returned.",
        },
        "surfaces": {
            "confirm": confirm_state(project),
            "svg_editor": editor_state(project),
            "storyboard": storyboard_state(project),
            "deck_review": deck_review_state(project),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project-local PPT Master interaction status projection")
    parser.add_argument("project", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(project_status(args.project), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"interaction_status: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
