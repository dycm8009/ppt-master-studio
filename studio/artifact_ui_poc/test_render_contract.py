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
    assert probe["response_transport"] == "direct-genui-app-block-content-reference"
    assert probe["transport_contract"] == "studio/artifact_ui_poc/CHATGPT_DIRECT_CONTENT_REFERENCE.md"
    assert probe["tool_discovery_required_for_render"] is False
    assert probe["tool_list_absence_is_unavailability_evidence"] is False

    contract = (ROOT / "CHATGPT_RENDER_CONTRACT.md").read_text(encoding="utf-8")
    assert "first inline render attempt is the capability probe" in contract
    assert 'app_block.entrypoint     = "index.html"' in contract
    assert "app_block.bundle_version = 1" in contract
    assert 'genui{"app_block":' in contract
    assert "do **not** require an `app_block` tool to be preloaded" in contract
    assert "absence from the tool list" in contract
    assert "HTML attachment" in contract

    direct = (ROOT / "CHATGPT_DIRECT_CONTENT_REFERENCE.md").read_text(encoding="utf-8")
    assert 'genui{"app_block":' in direct
    assert "rather than invoked as a normal tool call" in direct
    assert "Absence from the tool/action list is **not** evidence" in direct
    assert "Do not claim `current host has no inline app_block interface`" in direct

    project_instructions = (STUDIO / "CHATGPT_PROJECT_INSTRUCTIONS.txt").read_text(encoding="utf-8")
    assert "artifact-first active probe" in project_instructions
    assert "direct response content reference 本身就是本会话 host capability probe" in project_instructions
    assert 'genui{"app_block":' in project_instructions
    assert "工具列表里没有 `app_block`" in project_instructions
    assert "仅仅看不到 `app_block` tool/action 不是 fallback 证据" in project_instructions
    assert "缺少 callback 只影响 handoff" in project_instructions

    host_rules = (STUDIO / "enforcement" / "PPT_MASTER_HOST_CAPABILITY_RULES.md").read_text(encoding="utf-8")
    assert "## 8. Chat-inline artifact active probe" in host_rules
    assert 'genui{"app_block":' in host_rules
    assert "response-serialization capability" in host_rules
    assert "Do **not** require a previous chat" in host_rules
    assert "absence of an `app_block` tool/action" in host_rules
    assert "Never classify `current host has no inline app_block interface`" in host_rules

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
