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

    def test_rebuilt_asset_roster_rejects_old_user_response(self) -> None:
        images = self.project / "images"
        images.mkdir()
        asset = images / "shape.svg"
        asset.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="3"/></svg>')
        self.svg.write_text(SVG.replace("</svg>", '<image href="../images/shape.svg"/></svg>'))
        old = review.build(self.project)
        asset.write_text(asset.read_text().replace('r="3"', 'r="4"'))
        new = review.build(self.project)
        self.assertNotEqual(new["svg_roster_sha256"], old["svg_roster_sha256"])
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(old))

    def test_rejects_missing_or_added_slides(self) -> None:
        handoff = review.build(self.project)
        added = self.svg.with_name("P02.svg")
        added.write_text(SVG)
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))
        added.unlink()
        self.svg.unlink()
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))

    def test_invalid_current_xml_is_reported_as_stale(self) -> None:
        review.build(self.project)
        self.svg.write_text('<svg>')
        self.assertTrue(interaction.deck_review_state(self.project)["stale"])

    def test_changed_html_cannot_approve(self) -> None:
        handoff = review.build(self.project)
        Path(handoff["launch_path"]).write_text('broken')
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))

    def test_review_uses_exporter_numeric_order(self) -> None:
        self.svg.rename(self.svg.with_name('P1.svg'))
        for number in (10, 2):
            self.svg.with_name(f'P{number}.svg').write_text(SVG)
        handoff = review.build(self.project)
        rows = json.loads(Path(handoff['manifest_path']).read_text())['slides']
        self.assertEqual([row['slide'] for row in rows], ['P1.svg', 'P2.svg', 'P10.svg'])

    def test_response_comments_are_preserved_verbatim(self) -> None:
        handoff = review.build(self.project)
        response = self.response(handoff)
        response['changes'] = [{'slide': 'P01.svg', 'ordinal': 1, 'comment': '  Literal comment  '}]
        review.apply_response(self.project, response)
        stored = json.loads((self.project / 'live_preview/deck_review_response.json').read_text())
        self.assertEqual(stored, response)

    def test_wrong_ordinal_and_nonstring_comment_are_rejected(self) -> None:
        handoff = review.build(self.project)
        for item in ({'slide':'P01.svg', 'ordinal':2, 'comment':'x'},
                     {'slide':'P01.svg', 'ordinal':1, 'comment':17}):
            with self.subTest(item=item):
                response = self.response(handoff)
                response['changes'] = [item]
                with self.assertRaises(RuntimeError):
                    review.apply_response(self.project, response)

    def test_corrupt_old_manifest_can_be_rebuilt_without_history(self) -> None:
        handoff = review.build(self.project)
        Path(handoff['manifest_path']).write_text('{"slides":42}')
        rebuilt = review.build(self.project)
        self.assertIsNone(rebuilt['previous_review'])

    def test_source_scripts_are_removed_and_root_style_is_preserved(self) -> None:
        self.svg.write_text(SVG.replace('viewBox=', 'style="fill:red" onload="bad()" viewBox=').replace('</svg>', '<script>bad()</script></svg>'))
        cleaned = review._sanitized_svg(self.svg)
        self.assertNotIn('<script', cleaned)
        self.assertNotIn('onload', cleaned)
        self.assertIn('fill:red', cleaned)

    def test_prepared_icon_is_expanded_and_bound(self) -> None:
        icons = self.project / 'icons/chunk-filled'
        icons.mkdir(parents=True)
        icon = icons / 'demo.svg'
        icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M0 0H16V16Z" fill="currentColor"/></svg>')
        self.svg.write_text(SVG.replace('</svg>', '<use data-icon="chunk-filled/demo" x="3" y="5" width="16" height="16"/></svg>'))
        handoff = review.build(self.project)
        self.assertIn('M0 0H16V16Z', Path(handoff['launch_path']).read_text())
        icon.write_text(icon.read_text().replace('H16', 'H12'))
        with self.assertRaises(RuntimeError):
            review.apply_response(self.project, self.response(handoff))

    def test_slide_ids_cannot_shadow_html_controls(self) -> None:
        self.svg.write_text(SVG.replace('<rect ', '<rect id="complete" ').replace('</svg>', '<use href="#complete"/></svg>'))
        cleaned = review._sanitized_svg(self.svg)
        self.assertNotIn('id="complete"', cleaned)
        self.assertIn('href="#review-', cleaned)

    def test_network_image_is_not_silently_left_external(self) -> None:
        self.svg.write_text(SVG.replace('</svg>', '<image href="https://example.invalid/asset.png"/></svg>'))
        with self.assertRaises(RuntimeError):
            review.build(self.project)

    def test_storyboard_json_tampering_is_not_authority(self) -> None:
        storyboard.build(self.project)
        path = self.project / 'live_preview/storyboard.json'
        value = json.loads(path.read_text())
        value['slides'][0]['title'] = 'not from the spec'
        write_json(path, value)
        self.assertTrue(storyboard.status(self.project)['stale'])

    def test_storyboard_risk_recognizes_cpp(self) -> None:
        self.spec.write_text(SPEC.replace('Explanation', 'C++'))
        self.assertIn('code-or-api', storyboard.parse_design_spec(self.spec)['slides'][0]['risk_tags'])

    def test_experiments_reject_stale_storyboard(self) -> None:
        sys.path.insert(0, str(ROOT / 'skills/ppt-master/experiments'))
        import semantic_review
        import representative_calibration
        storyboard.build(self.project)
        self.spec.write_text(SPEC + '\n<!-- changed -->')
        for module in (semantic_review, representative_calibration):
            with self.subTest(module=module.__name__), self.assertRaises(RuntimeError):
                module.load_storyboard(self.project)

    def test_semantic_heuristic_preserves_comparison_operators(self) -> None:
        sys.path.insert(0, str(ROOT / 'skills/ppt-master/experiments'))
        import semantic_review
        data = {'slides':[{'slide_id':'P01', 'core_message':'x > 0'}, {'slide_id':'P02', 'core_message':'x < 0'}]}
        issues = semantic_review.review(data)['issues']
        self.assertNotIn('adjacent-core-message-duplicate', [issue['category'] for issue in issues])

    def test_editor_cursor_is_not_a_current_content_receipt(self) -> None:
        write_json(self.project / 'live_preview/hosted_editor.json', {'session':'a'*48, 'remote_base':'https://example.invalid', 'applied_capture_count':99})
        self.assertFalse(interaction.editor_state(self.project)['applied'])

    def test_confirm_restart_does_not_reuse_old_result(self) -> None:
        import os
        confirm = self.project / 'confirm_ui'
        write_json(confirm / 'result.json', {'stage':'final', 'status':'confirmed'})
        write_json(confirm / 'template_options.json', {'schema_version':1, 'phase':'template', 'default_mode':'free_design', 'explicit_workspace_roots':[]})
        stamp = (confirm / 'result.json').stat().st_mtime_ns + 1000000000
        os.utime(confirm / 'template_options.json', ns=(stamp, stamp))
        write_json(confirm / 'hosted_browser_handoff.json', {'session':'a'*48, 'remote_base':'https://example.invalid', 'applied_capture_count':2})
        state = interaction.confirm_state(self.project)
        self.assertFalse(state['validated'])
        self.assertNotEqual(state['next_action'], 'continue-after-final-confirmation')


    def test_assert_approved_cli_rechecks_current_files(self) -> None:
        import subprocess
        command = [sys.executable, '-S', str(SCRIPTS / 'deck_review_handoff.py'), 'assert-approved', str(self.project)]
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        handoff = review.build(self.project)
        review.apply_response(self.project, self.response(handoff))
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.svg.write_text(SVG + '\n<!-- changed -->', encoding='utf-8')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
