#!/usr/bin/env python3
"""Experimental representative-page calibration selector.

Select high-risk pages from an already-built Storyboard so benchmark runs can
compare the current P01-only method gate with a possible future representative
coverage strategy. This script is non-authoritative: it never mutates SVGs,
Design Spec, workflow state, or Gate receipts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from console_encoding import configure_utf8_stdio  # noqa: E402

SCHEMA = "ppt-master-representative-calibration-experiment/v1"
WEIGHTS = {
    "chart-or-table": 6,
    "formula": 6,
    "code-or-api": 6,
    "dense-content": 5,
    "images": 4,
    "visualization": 3,
    "motion": 1,
    "source-sensitive": 1,
}


def load_storyboard(project: Path) -> dict[str, Any]:
    path = project.resolve() / "live_preview" / "storyboard.json"
    if not path.is_file():
        raise RuntimeError(f"storyboard missing: {path}; build storyboard_handoff first")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "ppt-master-storyboard-projection/v1":
        raise RuntimeError("unsupported storyboard schema")
    return value


def select(storyboard: dict[str, Any], limit: int = 2) -> dict[str, Any]:
    if limit < 0 or limit > 2:
        raise RuntimeError("experimental representative limit must be between 0 and 2")
    candidates = [
        slide
        for slide in storyboard.get("slides") or []
        if isinstance(slide, dict) and int(slide.get("ordinal", 0) or 0) > 1
    ]
    selected: list[dict[str, Any]] = []
    covered: set[str] = set()
    remaining = list(candidates)
    while remaining and len(selected) < limit:
        scored: list[tuple[int, int, dict[str, Any], set[str]]] = []
        for slide in remaining:
            tags = set(map(str, slide.get("risk_tags") or []))
            base = sum(WEIGHTS.get(tag, 0) for tag in tags)
            novelty = sum(WEIGHTS.get(tag, 0) for tag in tags - covered)
            score = base + novelty
            scored.append((score, -int(slide.get("ordinal", 0) or 0), slide, tags))
        score, _, best, tags = max(scored, key=lambda row: (row[0], row[1]))
        if score <= 0:
            break
        selected.append(
            {
                "slide_id": best.get("slide_id"),
                "ordinal": best.get("ordinal"),
                "title": best.get("title"),
                "risk_tags": sorted(tags),
                "score": score,
            }
        )
        covered.update(tags)
        remaining = [slide for slide in remaining if slide is not best]
    return {
        "schema": SCHEMA,
        "experiment_only": True,
        "generation_rhythm_changed": False,
        "baseline": "current P01 first-page gate + uninterrupted remaining-page generation",
        "max_targets": limit,
        "selected": selected,
        "covered_risk_tags": sorted(covered),
    }


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Select representative pages for an offline calibration experiment"
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--max-targets", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        result = select(load_storyboard(args.project), args.max_targets)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"representative_calibration: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
