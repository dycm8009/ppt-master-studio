#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("rep_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module(ROOT / "skills/ppt-master/experiments/representative_calibration.py")
    storyboard = {
        "slides": [
            {"slide_id": "P01", "ordinal": 1, "title": "cover", "risk_tags": []},
            {"slide_id": "P02", "ordinal": 2, "title": "dense", "risk_tags": ["dense-content"]},
            {
                "slide_id": "P03",
                "ordinal": 3,
                "title": "chart",
                "risk_tags": ["chart-or-table", "visualization"],
            },
            {"slide_id": "P04", "ordinal": 4, "title": "code", "risk_tags": ["code-or-api"]},
        ]
    }
    result = module.select(storyboard, 2)
    assert result["experiment_only"] is True and result["generation_rhythm_changed"] is False
    assert [row["slide_id"] for row in result["selected"]] == ["P03", "P04"]
    assert "chart-or-table" in result["covered_risk_tags"]
    assert "code-or-api" in result["covered_risk_tags"]
    print("representative calibration experiment: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
