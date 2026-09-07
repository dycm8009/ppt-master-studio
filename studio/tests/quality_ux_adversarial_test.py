#!/usr/bin/env python3
"""Adversarial regression for the quality/UX roadmap; synthetic projects only."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/ppt-master/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "studio/host/cloudflare"))
import deck_review_handoff as review
import storyboard_handoff as storyboard
import interaction_status as interaction

SPEC = """<!-- ppt-master-schema: design-spec/v1 -->
# Synthetic - Design Spec
## I. Project Information
| Item | Value |
| --- | --- |
| Page Count | 1 |
## IX. Content Outline
#### Slide 01 - Example
- **Audience move**: unknown -> understood
- **Title**: Example
- **Core message**: Preserve the contract
- **Layout**: one column
- **Content**: Explanation
## X. Speaker Notes Requirements
- **Generation**: disabled
"""
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#ffffff"/><text x="50" y="80">Synthetic page</text></svg>'


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class QualityUXTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "svg_output").mkdir()
        self.svg = self.project / "svg_output/P01.svg"
        self.svg.write_text(SVG, encoding="utf-8")
        self.spec = self.project / "design_spec.md"
        self.spec.write_text(SPEC, encoding="utf-8")

    def response(self, handoff: dict) -> dict:
        return {"schema": review.RESPONSE_SCHEMA, "surface": "deck-review", "status": "user-confirmed", "svg_roster_sha256": handoff["svg_roster_sha256"], "changes": []}

    def test_apply_rejects_live_svg_mutation_without_rebuild(self) -> None:
        handoff = review.build(self.project)
        self.svg.write_text(SVG + "\n<!-- changed -->", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))
        self.assertFalse((self.project / "live_preview/deck_review_receipt.json").exists())

    def test_status_rejects_live_svg_mutation(self) -> None:
        handoff = review.build(self.project)
        review.apply_response(self.project, self.response(handoff))
        self.svg.write_text(SVG + "\n<!-- changed -->", encoding="utf-8")
        state = interaction.deck_review_state(self.project)
        self.assertTrue(state["stale"])
        self.assertFalse(state["validated"])
        self.assertNotEqual(state["next_action"], "continue-to-export")

    def test_history_without_response_cannot_infer_approval(self) -> None:
        handoff = review.build(self.project)
        response = self.response(handoff)
        response["changes"] = [{"slide": "P01.svg", "ordinal": 1, "comment": "Repair density"}]
        review.apply_response(self.project, response)
        (self.project / "live_preview/deck_review_response.json").unlink()
        review.build(self.project)
        manifest = json.loads((self.project / "live_preview/deck_review_manifest.json").read_text())
        self.assertIsNone(manifest["slides"][0]["previous_decision"])

    def test_html_namespace_serializes_as_real_inline_svg(self) -> None:
        svg = review._sanitized_svg(self.svg)
        self.assertRegex(svg, r"^<svg(?:\s|>)")
        self.assertNotIn("<ns0:svg", svg)

    def test_review_embeds_local_image_assets(self) -> None:
        import base64
        images = self.project / "images"
        images.mkdir()
        images.joinpath("one.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII="))
        self.svg.write_text(SVG.replace("</svg>", '<image href="../images/one.png" width="10" height="10"/></svg>'), encoding="utf-8")
        handoff = review.build(self.project)
        page = Path(handoff["launch_path"]).read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,", page)

    def test_asset_mutation_invalidates_review(self) -> None:
        import base64
        images = self.project / "images"
        images.mkdir()
        asset = images / "one.png"
        asset.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII="))
        self.svg.write_text(SVG.replace("</svg>", '<image href="../images/one.png" width="10" height="10"/></svg>'), encoding="utf-8")
        handoff = review.build(self.project)
        asset.write_bytes(asset.read_bytes() + b"modified")
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))

    def test_storyboard_missing_spec_is_stale(self) -> None:
        storyboard.build(self.project)
        self.spec.unlink()
        self.assertTrue(interaction.storyboard_state(self.project)["stale"])

    def test_storyboard_missing_html_is_not_current(self) -> None:
        storyboard.build(self.project)
        (self.project / "live_preview/storyboard.html").unlink()
        self.assertNotEqual(storyboard.status(self.project)["status"], "current")

    def test_storyboard_preserves_indentation_and_ignores_fenced_headings(self) -> None:
        code = "```cpp\nvoid f() {\n    work();\n}\n#### Slide 99 - literal code\n- **Title**: not a field\n```"
        self.spec.write_text(SPEC.replace("- **Content**: Explanation", "- **Content**: Example\n" + code), encoding="utf-8")
        result = storyboard.parse_design_spec(self.spec)
        self.assertEqual(result["slide_count"], 1)
        self.assertIn("    work();", result["slides"][0]["content"])
        self.assertIn("#### Slide 99", result["slides"][0]["content"])

    def test_duplicate_page_identity_is_rejected(self) -> None:
        extra = "#### Slide 01 - Duplicate\n- **Content**: duplicate\n"
        self.spec.write_text(SPEC.replace("## X.", extra + "## X."), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            storyboard.parse_design_spec(self.spec)

    def test_missing_changes_count_cannot_signal_export(self) -> None:
        handoff = review.build(self.project)
        review.apply_response(self.project, self.response(handoff))
        path = self.project / "live_preview/deck_review_receipt.json"
        receipt = json.loads(path.read_text())
        receipt.pop("changes_count")
        write_json(path, receipt)
        state = interaction.deck_review_state(self.project)
        self.assertFalse(state["validated"])
        self.assertNotEqual(state["next_action"], "continue-to-export")


if __name__ == "__main__":
    unittest.main(verbosity=2)
