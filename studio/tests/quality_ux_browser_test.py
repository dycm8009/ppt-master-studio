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
        self.project = project
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
        self.assertTrue(self.page.locator('#complete').is_disabled())
        self.assertFalse(self.page.locator('#result-json').input_value())

    def test_mobile_controls_do_not_overflow(self) -> None:
        self.page.set_viewport_size({'width':390, 'height':844})
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        self.assertGreater(self.page.locator('#canvas svg').bounding_box()['width'], 100)

    def test_no_history_is_automatically_checked(self) -> None:
        self.assertEqual(self.page.locator('input[name="decision"]:checked').count(), 0)
        self.assertTrue(self.page.locator('#complete').is_disabled())


    def test_history_does_not_preselect_new_approval(self) -> None:
        import json
        self.approve_all()
        review.apply_response(self.project, json.loads(self.page.locator('#result-json').input_value()))
        handoff = review.build(self.project)
        self.page.goto(Path(handoff['launch_path']).as_uri())
        self.assertIn('上次决定：通过', self.page.locator('#history').text_content())
        self.assertEqual(self.page.locator('input[name="decision"]:checked').count(), 0)
        self.assertTrue(self.page.locator('#complete').is_disabled())

    def test_local_image_is_decodable_after_html_relocation(self) -> None:
        import base64
        images = self.project / 'images'
        images.mkdir()
        (images / 'one.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII='))
        slide = self.project / 'svg_output/P01.svg'
        slide.write_text(slide.read_text().replace('</svg>', '<image href="../images/one.png" width="50" height="50"/></svg>'))
        handoff = review.build(self.project)
        relocated = self.project / 'relocated.html'
        relocated.write_bytes(Path(handoff['launch_path']).read_bytes())
        self.page.goto(relocated.as_uri())
        href = self.page.locator('#canvas image').get_attribute('href')
        self.assertTrue(href.startswith('data:image/png;base64,'))
        dimensions = self.page.evaluate("""async (url) => {const img=new Image();img.src=url;await img.decode();return [img.naturalWidth,img.naturalHeight]}""", href)
        self.assertEqual(dimensions, [1, 1])

    def test_portrait_review_retains_canvas_ratio(self) -> None:
        slide = self.project / 'svg_output/P01.svg'
        slide.write_text(slide.read_text().replace('0 0 1280 720', '0 0 720 1280'))
        handoff = review.build(self.project)
        self.page.goto(Path(handoff['launch_path']).as_uri())
        ratio = self.page.locator('#canvas').evaluate('(el) => el.style.aspectRatio')
        self.assertEqual(ratio.replace(' ', ''), '720/1280')

    def test_storyboard_displays_code_and_escapes_markup(self) -> None:
        import storyboard_handoff
        spec = """## I. Project Information
| Page Count | 1 |
## IX. Content Outline
#### Slide 01 - Code example
- **Title**: <img src=x onerror="window.qaInjected=true">
- **Audience move**: unknown -> understood
- **Core message**: Preserve code
- **Content**: Example
```cpp
void f() {
    work();
}
#### Slide 99 - literal
```
## X. Speaker Notes Requirements
- **Generation**: disabled
"""
        (self.project / 'design_spec.md').write_text(spec, encoding='utf-8')
        handoff = storyboard_handoff.build(self.project)
        self.page.goto(Path(handoff['launch_path']).as_uri())
        self.assertEqual(self.page.locator('.item').count(), 1)
        self.assertIn('    work();', self.page.locator('#card').text_content())
        self.assertEqual(self.page.locator('#card img').count(), 0)
        self.assertFalse(self.page.evaluate('Boolean(window.qaInjected)'))
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
