#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("storyboard_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module(ROOT / "skills/ppt-master/scripts/storyboard_handoff.py")
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        (project / "design_spec.md").write_text(
            """<!-- ppt-master-schema: design-spec/v1 -->
# Demo - Design Spec
## I. Project Information
x
## IX. Content Outline
### Part 1: Why
#### Slide 01 - Cover
- **Audience move**: unknown → oriented
- **Layout**: strong title
- **Title**: AI-friendly architecture
- **Core message**: Architecture must expose boundaries.
- **Content**: One concise thesis.
- **Fact IDs**: F-01
#### Slide 02 - Evidence
- **Audience move**: oriented → convinced
- **Layout**: left evidence, right diagram
- **Title**: Feedback loops make architecture operable
- **Core message**: Observability closes the loop.
- **Content**: API contract, code snippet, telemetry, test loop.
- **Visualization**: table comparing before and after
- **Native-ready**: comparison=yes
- **Motion suggestion**: reveal feedback loop in order
## X. Speaker Notes Requirements
- **Generation**: disabled
""",
            encoding="utf-8",
        )
        handoff = module.build(project)
        assert handoff["slide_count"] == 2 and handoff["blocking"] is False
        data = json.loads((project / "live_preview/storyboard.json").read_text(encoding="utf-8"))
        assert data["slides"][0]["previous_slide"] is None
        assert data["slides"][1]["previous_slide"] == "P01"
        assert "source-sensitive" in data["slides"][0]["risk_tags"]
        assert "chart-or-table" in data["slides"][1]["risk_tags"]
        assert "code-or-api" in data["slides"][1]["risk_tags"]
        assert module.status(project)["stale"] is False
        (project / "design_spec.md").write_text(
            (project / "design_spec.md").read_text(encoding="utf-8") + "\n<!-- mutation -->\n",
            encoding="utf-8",
        )
        assert module.status(project)["stale"] is True

    print("storyboard handoff: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
