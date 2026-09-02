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
        for n, fill in ((1, "#111111"), (2, "#222222")):
            (out / f"P{n:02d}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
                f'<rect width="1280" height="720" fill="{fill}"/>'
                f'<text x="80" y="120" fill="#ffffff">Page {n}</text></svg>',
                encoding="utf-8",
            )
        handoff = module.build(project)
        assert handoff["status"] == "ready" and handoff["slide_count"] == 2
        html = Path(handoff["launch_path"]).read_text(encoding="utf-8")
        assert "Page 1" in html and "Page 2" in html
        assert "ppt-master-static-deck-review-response/v1" in html
        response = {
            "schema": "ppt-master-static-deck-review-response/v1",
            "surface": "deck-review",
            "status": "user-confirmed",
            "svg_roster_sha256": handoff["svg_roster_sha256"],
            "changes": [{"slide": "P02.svg", "ordinal": 2, "comment": "Reduce density."}],
        }
        receipt = module.apply_response(project, response)
        assert receipt["status"] == "validated-and-persisted-by-pinned-harness"
        assert receipt["result"] == "changes-requested" and receipt["changes_count"] == 1

        # Any SVG mutation invalidates the old approval hash.
        (out / "P02.svg").write_text((out / "P02.svg").read_text() + "\n<!-- changed -->\n")
        newer = module.build(project)
        assert newer["svg_roster_sha256"] != handoff["svg_roster_sha256"]
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
