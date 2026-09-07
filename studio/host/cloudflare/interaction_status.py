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
import sys
from pathlib import Path
from typing import Any

PROJECT_SCHEMA = "ppt-master-project-interaction-state/v1"
SURFACE_SCHEMA = "ppt-master-interaction-surface-state/v1"


def _load_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
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
    state = direct or browser or {}
    if not confirm.is_dir():
        return _surface("confirm", authority="pinned-official-confirm-api", next_action="open-confirm-surface")
    # Reuse the pinned core's pure state builder: it owns stage progression and
    # the fresh-template restart rule. Do not reinterpret a cached result here.
    official = _harness_module("confirm_ui.server")._build_session_state(confirm)
    active_stage = official.get("current_stage")
    result_stage = official.get("result_stage")
    validated = result_stage == "final" or (active_stage == "stage1" and result_stage == "stage1")
    pin = (_load_object(project / "project_state.json") or {}).get("harness", {})
    mismatched_pin = bool(isinstance(pin, dict) and pin.get("commit") and state.get("harness_commit")
                          and pin["commit"] != state["harness_commit"])
    ambiguous = bool(direct and browser and direct.get("session") != browser.get("session"))
    stale = mismatched_pin or ambiguous
    if stale:
        validated = False
        action = "resolve-active-pinned-transport"
    elif result_stage == "final":
        action = "continue-after-final-confirmation"
    elif result_stage == "stage1" and active_stage != "stage2":
        handoff = _load_object(confirm / "template_handoff.json")
        action = "author-or-present-stage2" if handoff and handoff.get("status") == "ready" else "complete-template-handoff"
    elif browser:
        action = "present-launch-or-apply-copied-json"
    elif direct:
        action = "present-launch-or-pull-and-apply"
    else:
        action = "use-official-confirm-surface"
    return _surface("confirm", authority="pinned-official-confirm-api", generated=bool(state or result_stage),
                    launch_ready=bool(state.get("session") and state.get("remote_base") and not stale),
                    user_submitted=bool(result_stage and not stale), validated=validated, applied=validated,
                    stale=stale, next_action=action,
                    details={"transport_mode": state.get("transport_mode"), "feedback_mode": state.get("feedback_mode"),
                             "active_stage": active_stage, "result_stage": result_stage,
                             "harness_commit": state.get("harness_commit"),
                             "pending_remote_capture": None, "remote_accessibility": "not-probed",
                             "official_status": official.get("status"), "official_error": official.get("template_error")})


def editor_state(project: Path) -> dict[str, Any]:
    state = _load_object(project / "live_preview" / "hosted_editor.json")
    if not state:
        return _surface(
            "svg-editor",
            authority="pinned-official-svg-editor",
            next_action="open-editor-if-route-requires-it",
        )
    count = state.get("applied_capture_count")
    count = count if type(count) is int and count >= 0 else 0
    # A transport cursor is historical evidence, not a content-bound receipt
    # for the current SVG version or evidence of pending remote edits.
    return _surface("svg-editor", generated=True,
                    launch_ready=bool(state.get("session") and state.get("remote_base")),
                    authority="pinned-official-svg-editor",
                    next_action="continue-generation-or-apply-new-editor-captures",
                    details={"historical_applied_capture_count": count,
                             "current_content_validation": "not-proven-by-transport-cursor",
                             "pending_remote_capture": None, "remote_accessibility": "not-probed"})


def _harness_module(name: str):
    scripts = Path(__file__).resolve().parents[3] / "skills/ppt-master/scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import importlib.util
    source = scripts / (name.replace(".", "/") + ".py")
    spec = importlib.util.spec_from_file_location("ppt_master_status_" + name.replace(".", "_"), source)
    if not spec or not spec.loader:
        raise RuntimeError(f"pinned Harness module unavailable: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deck_review_state(project: Path) -> dict[str, Any]:
    observed = _harness_module("deck_review_handoff").review_status(project)
    return _surface("deck-review", authority="pinned-deck-review-handoff",
                    **{key: observed[key] for key in ("generated", "launch_ready", "user_submitted",
                                                     "validated", "applied", "stale", "next_action")},
                    details={**observed, "scope": "Deck Review only; other official export gates still apply"})


def storyboard_state(project: Path) -> dict[str, Any]:
    observed = _harness_module("storyboard_handoff").status(project)
    return _surface("storyboard", authority="design-spec-read-only-projection",
                    generated=(project / "live_preview/storyboard.json").is_file(),
                    launch_ready=observed.get("status") == "current", stale=observed.get("stale", False),
                    next_action="optional-read-only-review" if observed.get("status") == "current" else
                                "rebuild-storyboard", details=observed)


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
        print(f"interaction_status: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
