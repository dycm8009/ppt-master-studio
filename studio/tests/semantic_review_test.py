#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("sem_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module(ROOT / "skills/ppt-master/experiments/semantic_review.py")
    storyboard = {
        "slides": [
            {
                "slide_id": "P01",
                "title": "A",
                "core_message": "Same",
                "audience_move": "x → y",
                "layout": "",
                "visualization": "",
                "risk_tags": [],
            },
            {
                "slide_id": "P02",
                "title": "B",
                "core_message": "Same",
                "audience_move": "",
                "layout": "",
                "visualization": "",
                "risk_tags": ["dense-content"],
            },
        ]
    }
    result = module.review(storyboard)
    categories = {item["category"] for item in result["issues"]}
    assert result["blocking"] is False
    assert "adjacent-core-message-duplicate" in categories
    assert "missing-audience-move" in categories
    assert "dense-without-layout-intent" in categories
    required = {
        "page_id",
        "category",
        "severity",
        "evidence",
        "expected_semantic_relationship",
        "suggested_repair_scope",
    }
    assert all(required <= set(item) for item in result["issues"])
    print("semantic review experiment: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
