from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STUDIO = ROOT.parent


def main() -> int:
    caps = json.loads((ROOT / "HOST_CAPABILITIES.json").read_text(encoding="utf-8"))
    probe = caps["probe_policy"]
    assert probe["mode"] == "artifact-first-active-probe"
    assert probe["probe_each_conversation"] is True
    assert probe["prior_chat_evidence_required"] is False
    assert probe["build_artifact_before_static_ui_fallback"] is True
    assert probe["fallback_only_on_explicit_unavailability_or_render_failure"] is True
    assert probe["render_contract"] == "studio/artifact_ui_poc/CHATGPT_RENDER_CONTRACT.md"

    contract = (ROOT / "CHATGPT_RENDER_CONTRACT.md").read_text(encoding="utf-8")
    assert "first inline render attempt is the capability probe" in contract
    assert 'app_block.entrypoint    = "index.html"' in contract
    assert "app_block.bundle_version = 1" in contract
    assert "Do not choose Static UI merely because" in contract
    assert "HTML attachment" in contract

    project_instructions = (STUDIO / "CHATGPT_PROJECT_INSTRUCTIONS.txt").read_text(encoding="utf-8")
    assert "artifact-first active probe" in project_instructions
    assert "渲染尝试本身就是本会话的 host capability probe" in project_instructions
    assert "不得因为“这是新聊天”" in project_instructions
    assert "缺少 callback 只影响 handoff" in project_instructions
    assert "不得仅因为当前聊天缺少历史 host 验证而 fallback" in project_instructions

    host_rules = (STUDIO / "enforcement" / "PPT_MASTER_HOST_CAPABILITY_RULES.md").read_text(encoding="utf-8")
    assert "## 8. Chat-inline artifact active probe" in host_rules
    assert "Do **not** require a previous chat" in host_rules
    assert "Do **not** pre-build or present Static UI HTML" in host_rules

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
