#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("deck_review_handoff_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    here = Path(__file__).resolve().parent
    repo = here.parent.parent
    module = load_module(repo / "skills" / "ppt-master" / "scripts" / "deck_review_handoff.py")
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        out = project / "svg_output"
        out.mkdir()
        for number, fill in ((1, "#111111"), (2, "#222222")):
            (out / f"P{number:02d}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
                f'<rect width="1280" height="720" fill="{fill}"/>'
                f'<text x="80" y="120" fill="#ffffff">Page {number}</text></svg>',
                encoding="utf-8",
            )

        handoff = module.build(project)
        assert handoff["status"] == "ready" and handoff["slide_count"] == 2
        assert handoff["changed_slide_count"] == 2 and handoff["previous_review"] is None
        html = Path(handoff["launch_path"]).read_text(encoding="utf-8")
        assert "Page 1" in html and "历史信息只用于定位变化" in html

        response = {
            "schema": "ppt-master-static-deck-review-response/v1",
            "surface": "deck-review",
            "status": "user-confirmed",
            "svg_roster_sha256": handoff["svg_roster_sha256"],
            "changes": [{"slide": "P02.svg", "ordinal": 2, "comment": "Reduce density."}],
        }
        receipt = module.apply_response(project, response)
        assert receipt["result"] == "changes-requested" and receipt["reviewed_slide_count"] == 2

        unchanged = module.build(project)
        assert unchanged["changed_slide_count"] == 0
        manifest = json.loads(Path(unchanged["manifest_path"]).read_text(encoding="utf-8"))
        by_slide = {row["slide"]: row for row in manifest["slides"]}
        assert by_slide["P01.svg"]["review_delta"] == "unchanged"
        assert by_slide["P01.svg"]["previous_decision"] == "approved"
        assert by_slide["P02.svg"]["previous_decision"] == "changes"

        (out / "P02.svg").write_text(
            (out / "P02.svg").read_text(encoding="utf-8") + "\n<!-- changed -->\n",
            encoding="utf-8",
        )
        newer = module.build(project)
        assert newer["svg_roster_sha256"] != handoff["svg_roster_sha256"]
        assert newer["changed_slide_count"] == 1
        manifest = json.loads(Path(newer["manifest_path"]).read_text(encoding="utf-8"))
        by_slide = {row["slide"]: row for row in manifest["slides"]}
        assert by_slide["P02.svg"]["review_delta"] == "changed"
        assert newer["previous_review"]["approval_reuse_allowed"] is False

        try:
            module.apply_response(project, response)
        except RuntimeError as exc:
            assert "roster hash mismatch" in str(exc)
        else:
            raise AssertionError("stale review response was accepted")

    print("framework-free deck review handoff: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
