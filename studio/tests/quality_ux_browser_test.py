#!/usr/bin/env python3
"""Real Chromium regression of the actual-SVG handoff, not screenshot approval."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/ppt-master/scripts"))
import deck_review_handoff as review


class ReviewBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        project = Path(self.tmp.name)
        out = project / "svg_output"
        out.mkdir()
        for index in (1, 2):
            (out / f"P{index:02d}.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><text x="50" y="80">Actual page ' + str(index) + '</text></svg>', encoding="utf-8")
        handoff = review.build(project)
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 900})
        self.addCleanup(self.page.close)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(Path(handoff["launch_path"]).as_uri())

    def approve_all(self) -> None:
        for _ in (1, 2):
            self.page.locator('input[value="approved"]').check()
            self.page.locator('#save-next').click()
        self.page.locator('#complete').click()

    def test_actual_svg_is_visible(self) -> None:
        svg = self.page.locator('#canvas svg')
        self.assertEqual(svg.count(), 1)
        self.assertEqual(svg.evaluate('(el) => el.namespaceURI'), 'http://www.w3.org/2000/svg')
        self.assertGreater(svg.bounding_box()['width'], 100)
        self.assertIn('Actual page 1', svg.text_content())
        self.assertEqual(self.errors, [])

    def test_edit_after_completion_invalidates_copy(self) -> None:
        self.approve_all()
        self.assertTrue(self.page.locator('#result-json').input_value())
        self.page.locator('#prev').click()
        self.page.locator('input[value="changes"]').check()
        self.page.locator('#comment').fill('Keep the facts; repair the layout')
        self.assertEqual(self.page.locator('#result-json').input_value(), '')
        self.assertFalse(self.page.locator('#copy-area').is_visible())
        self.page.locator('#save-next').click()
        self.page.locator('#complete').click()
        self.assertIn('repair the layout', self.page.locator('#result-json').input_value())

    def test_clipboard_failure_is_not_success(self) -> None:
        self.approve_all()
        self.page.evaluate("""() => {
            Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async () => {throw new Error('denied')}}});
            document.execCommand = () => false;
        }""")
        self.page.locator('#copy').click()
        self.assertNotEqual(self.page.locator('#copy').text_content(), '已复制')

    def test_invalid_change_does_not_restore_prior_approval(self) -> None:
        self.approve_all()
        self.page.locator('#prev').click()
        self.page.locator('input[value="changes"]').check()
        self.page.locator('#comment').fill('')
        self.page.locator('#next').click()
        self.page.locator('#complete').click(force=True)
        self.assertFalse(self.page.locator('#result-json').input_value())


if __name__ == '__main__':
    unittest.main(verbosity=2)
