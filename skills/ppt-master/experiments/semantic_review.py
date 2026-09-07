#!/usr/bin/env python3
"""Deterministic semantic-review baseline for PPT Master benchmark work.

This is advisory experiment infrastructure, not a Generate quality gate. It
operates on the read-only Storyboard projection and emits page-addressable issue
objects using the roadmap's evidence/relationship/repair-scope contract.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from console_encoding import configure_utf8_stdio  # noqa: E402

SCHEMA = "ppt-master-semantic-review-experiment/v1"


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def _issue(
    slide: dict[str, Any],
    category: str,
    severity: str,
    evidence: str,
    expected: str,
    repair: str,
) -> dict[str, Any]:
    return {
        "page_id": slide.get("slide_id"),
        "category": category,
        "severity": severity,
        "evidence": evidence,
        "expected_semantic_relationship": expected,
        "suggested_repair_scope": repair,
    }


def review(storyboard: dict[str, Any]) -> dict[str, Any]:
    slides = [slide for slide in storyboard.get("slides") or [] if isinstance(slide, dict)]
    issues: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for slide in slides:
        if not str(slide.get("title") or "").strip():
            issues.append(
                _issue(
                    slide,
                    "missing-title",
                    "advisory",
                    "Storyboard title is empty.",
                    "Each page needs an identifiable page claim/topic.",
                    "Strategist: repair this page title only.",
                )
            )
        if not str(slide.get("core_message") or "").strip():
            issues.append(
                _issue(
                    slide,
                    "missing-core-message",
                    "advisory",
                    "Core message is empty.",
                    "Each page should have one governing assertion when the format supports it.",
                    "Strategist: repair this page core message only.",
                )
            )
        if not str(slide.get("audience_move") or "").strip():
            issues.append(
                _issue(
                    slide,
                    "missing-audience-move",
                    "advisory",
                    "Audience move is empty.",
                    "The page should advance audience state rather than only contain material.",
                    "Strategist: clarify before/after audience state for this page.",
                )
            )
        tags = set(map(str, slide.get("risk_tags") or []))
        if "dense-content" in tags and not str(slide.get("layout") or "").strip():
            issues.append(
                _issue(
                    slide,
                    "dense-without-layout-intent",
                    "advisory",
                    "Dense content risk is present but Layout is empty.",
                    "Dense material needs a stated hierarchy/focus before geometry.",
                    "Strategist: add non-binding hierarchy/layout intent; do not prescribe coordinates.",
                )
            )
        if "chart-or-table" in tags and not str(slide.get("visualization") or "").strip():
            issues.append(
                _issue(
                    slide,
                    "data-visual-without-visualization-contract",
                    "advisory",
                    "Chart/table risk inferred but Visualization is empty.",
                    "Value-driven geometry should have an explicit semantic visualization role.",
                    "Strategist: name the data relationship and intended visual job.",
                )
            )
        if previous:
            previous_message = _norm(str(previous.get("core_message") or ""))
            current_message = _norm(str(slide.get("core_message") or ""))
            if previous_message and previous_message == current_message:
                issues.append(
                    _issue(
                        slide,
                        "adjacent-core-message-duplicate",
                        "advisory",
                        f"Core message duplicates {previous.get('slide_id')}: {slide.get('core_message')}",
                        "Adjacent pages should normally advance, qualify, evidence, or transform the argument.",
                        "Strategist: merge pages or differentiate the second page job without changing sourced facts.",
                    )
                )
        previous = slide
    return {
        "schema": SCHEMA,
        "experiment_only": True,
        "design_spec_sha256": storyboard.get("design_spec_sha256"),
        "blocking": False,
        "slide_count": len(slides),
        "issue_count": len(issues),
        "coverage": "structural text heuristics only; facts, visual topology and PPTX rendering are not verified",
        "issues": issues,
    }


def load_storyboard(project: Path) -> dict[str, Any]:
    from storyboard_handoff import load_current
    return load_current(project)


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Run advisory semantic-review baseline over Storyboard"
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = review(load_storyboard(args.project))
        output = args.output or (
            args.project.resolve() / "validation" / "semantic_review_experiment.json"
        )
        output = output.resolve()
        if not output.is_relative_to(args.project.resolve() / "validation"):
            raise RuntimeError("experiment output must stay under project/validation; source artifacts are read-only")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "completed",
                    "output": str(output),
                    "issue_count": result["issue_count"],
                    "blocking": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(f"semantic_review: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
