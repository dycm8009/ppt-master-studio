#!/usr/bin/env python3
"""Hermetic regression for the released ChatGPT Runtime bundle.

This test deliberately launches the extracted Runtime with ``python -S`` so
third-party site-packages, including Flask, are unavailable. It proves that:

* runtime ZIP paths retain Unicode template names;
* Cloudflare browser handoff can complete Stage 1 and Stage 2 headlessly;
* the outbound-HTTPS bridge defaults to the same headless official API core;
* official receipts are still written by pinned ``confirm_ui/server.py`` logic.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
COMMIT = "1" * 40
BASE = "https://ppt-master-hosted.example"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_no_site(*args: object) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [PY, "-S", *map(str, args)],
        text=True,
        capture_output=True,
        timeout=90,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"headless command failed: {args}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}"
        )
    return proc


def stage1_recommendation() -> dict:
    return {
        "stage": "stage1",
        "lang": "zh",
        "primary_language": "zh-CN",
        "recommend": {"canvas": "ppt169"},
        "audience": {"value": "C++ 开发工程师"},
        "communication_intent": {"value": "解释 AI 友好型架构并形成工程决策"},
        "audience_outcome": {"value": "理解关键系统边界"},
        "core_message": {"value": "可验证、可观测、可执行"},
        "delivery_context": {"value": "技术分享"},
        "artifact_afterlife": {"value": "设计评审参考"},
        "content_divergence": {"value": ""},
    }


def stage1_payload() -> dict:
    return {
        "stage": "stage1",
        "primary_language": "zh-CN",
        "canvas": "ppt169",
        "audience": "C++ 开发工程师",
        "communication_intent": "解释 AI 友好型架构并形成工程决策",
        "audience_outcome": "理解关键系统边界",
        "core_message": "可验证、可观测、可执行",
        "delivery_context": "技术分享",
        "artifact_afterlife": "设计评审参考",
        "content_divergence": "",
        "template_selection": {"mode": "free_design", "selection_keys": []},
    }


def direction(index: int) -> dict:
    accents = ["#2D7FF9", "#E66C63", "#C85C3C"]
    return {
        "id": f"direction-{index}",
        "name_zh": f"方向 {index}",
        "mode": "custom",
        "mode_behavior_zh": f"以工程判断和证据链组织内容 {index}",
        "visual_style": "custom",
        "visual_style_behavior_zh": f"克制的技术信息设计 {index}",
        "color": {
            "name_zh": f"配色 {index}",
            "palette": {
                "background": "#F7F9FC",
                "secondary_bg": "#E8EEF5",
                "primary": "#18324A",
                "accent": accents[index - 1],
                "secondary_accent": "#4DB6AC",
                "body_text": "#243447",
            },
        },
        "typography": {
            "name_zh": f"字体 {index}",
            "heading": {"primary": "DengXian", "english": "Arial", "css": "sans-serif"},
            "body": {"primary": "Microsoft YaHei", "english": "Arial", "css": "sans-serif"},
            "body_size": 24,
        },
        "icons": "tabler-outline",
        "image_strategy": {
            "name_zh": f"图像策略 {index}",
            "rendering": "custom",
            "visual_zh": "结构化系统图与证据图",
            "mood_zh": "精确、可信",
            "behavior_zh": "仅使用具有明确技术解释目的的视觉",
        },
    }


def stage2_recommendation() -> dict:
    return {
        "stage": "stage2",
        "lang": "zh",
        "primary_language": "zh-CN",
        "recommend": {
            "canvas": "ppt169",
            "delivery_purpose": "balanced",
            "generation_mode": "continuous",
            "image_usage": ["none"],
        },
        "page_count": {"value": "12-15"},
        "design_directions": {
            "selected": 0,
            "candidates": [direction(1), direction(2), direction(3)],
        },
        "image_usage": {"value": ["none"]},
        "image_notes": {"value": "本测试不需要外部图片。"},
        "proactive_speaker_notes": {"value": True},
        "proactive_custom_animations": {"value": False},
        "proactive_narration_audio": {"value": False},
        "refine_spec": {"value": False},
    }


def final_payload() -> dict:
    return {
        "stage": "final",
        "canvas": "ppt169",
        "page_count": "12-15",
        "delivery_purpose": "balanced",
        "mode": "custom",
        "mode_behavior": "以工程判断和证据链组织内容",
        "visual_style": "custom",
        "visual_style_behavior": "克制的技术信息设计",
        "color": {
            "name": "custom",
            "palette": {
                "background": "#F7F9FC",
                "secondary_bg": "#E8EEF5",
                "primary": "#18324A",
                "accent": "#2D7FF9",
                "secondary_accent": "#4DB6AC",
                "body_text": "#243447",
            },
        },
        "typography": {
            "name": "custom",
            "heading": {"primary": "DengXian", "english": "Arial", "css": "sans-serif"},
            "body": {"primary": "Microsoft YaHei", "english": "Arial", "css": "sans-serif"},
            "body_size": 24,
            "body_size_unit": "px",
            "sizes": {"title": 42, "subtitle": 32, "annotation": 18},
        },
        "icons": "tabler-outline",
        "image_usage": ["none"],
        "image_notes": "本测试不需要外部图片。",
        "proactive_speaker_notes": True,
        "proactive_custom_animations": False,
        "proactive_narration_audio": False,
        "generation_mode": "continuous",
        "refine_spec": False,
    }


def initialize_project(project: Path) -> None:
    confirm = project / "confirm_ui"
    confirm.mkdir(parents=True)
    write_json(
        confirm / "template_options.json",
        {
            "schema_version": 1,
            "phase": "template",
            "default_mode": "free_design",
            "lang": "zh",
            "explicit_workspace_roots": [],
        },
    )
    write_json(confirm / "recommendations.stage1.json", stage1_recommendation())


def response(commit: str, captures: list[dict]) -> dict:
    return {
        "schema": "ppt-master-hosted-official-captured/v1",
        "status": "captured-not-validated",
        "harness_status": "not-validated",
        "harness_commit": commit,
        "active_stage": captures[-1]["stage"],
        "captures": captures,
        "session_status": "waiting-agent",
    }


def handoff_roundtrip(runtime: Path, project: Path) -> None:
    handoff = runtime / "studio/host/cloudflare/hosted_confirm_handoff.py"
    server = runtime / "skills/ppt-master/scripts/confirm_ui/server.py"
    opened = json.loads(
        run_no_site(handoff, "bootstrap-project", project, "--base", BASE, "--harness-commit", COMMIT).stdout
    )
    assert opened["stage"] == "stage1"
    assert opened["url"].startswith(BASE + "/#ppt-master-official-bootstrap-gz=")

    captures = [{"stage": "stage1", "payload": stage1_payload(), "captured_at": "2026-08-29T00:00:00Z"}]
    stage1_response = project / "response.stage1.json"
    write_json(stage1_response, response(COMMIT, captures))
    applied1 = json.loads(run_no_site(handoff, "apply-response", project, stage1_response, "--stage", "stage1").stdout)
    assert applied1["status"] == "validated-and-persisted-by-pinned-harness"

    run_no_site(server, project, "--complete-template-selection")
    handoff_receipt = json.loads((project / "confirm_ui/template_handoff.json").read_text(encoding="utf-8"))
    assert handoff_receipt["status"] == "ready"
    write_json(project / "confirm_ui/recommendations.stage2.json", stage2_recommendation())
    advanced = json.loads(run_no_site(handoff, "advance-project", project).stdout)
    assert advanced["stage"] == "stage2"

    captures.append({"stage": "stage2", "payload": final_payload(), "captured_at": "2026-08-29T00:01:00Z"})
    stage2_response = project / "response.stage2.json"
    write_json(stage2_response, response(COMMIT, captures))
    applied2 = json.loads(run_no_site(handoff, "apply-response", project, stage2_response, "--stage", "stage2").stdout)
    assert applied2["status"] == "validated-and-persisted-by-pinned-harness"
    result = json.loads((project / "confirm_ui/result.json").read_text(encoding="utf-8"))
    assert result["stage"] == "final" and result["status"] == "confirmed"


def bridge_probe(runtime: Path, project: Path) -> None:
    probe = project.parent / "bridge_probe.py"
    probe.write_text(
        """
import json
from pathlib import Path
import sys
runtime = Path(sys.argv[1])
project = Path(sys.argv[2])
sys.path.insert(0, str(runtime / 'studio/host/cloudflare'))
import hosted_confirm_bridge as bridge
bridge.create_remote_session = lambda *a, **k: {'expires_at': '2099-01-01T00:00:00Z'}
opened = bridge.open_hosted_confirm(
    project,
    '1' * 40,
    remote_base='https://ppt-master-hosted.example',
    session='2' * 48,
    host_key='3' * 64,
)
assert opened['local_authority'] == 'pinned-official-confirm-api:headless'
assert not (project / '.confirm_ui.lock').exists()
state = json.loads((project / 'confirm_ui/hosted_confirm.json').read_text(encoding='utf-8'))
assert state['authority_mode'] == 'headless-official-confirm-api'
payload = {
    'stage': 'stage1',
    'primary_language': 'zh-CN',
    'canvas': 'ppt169',
    'audience': 'C++ 开发工程师',
    'communication_intent': '解释 AI 友好型架构并形成工程决策',
    'audience_outcome': '理解关键系统边界',
    'core_message': '可验证、可观测、可执行',
    'delivery_context': '技术分享',
    'artifact_afterlife': '设计评审参考',
    'content_divergence': '',
    'template_selection': {'mode': 'free_design', 'selection_keys': []},
}
remote_response = {
    'status': 'captured-not-validated',
    'harness_status': 'not-validated',
    'harness_commit': '1' * 40,
    'captures': [{'stage': 'stage1', 'payload': payload}],
    'session_status': 'waiting-agent',
}
bridge._request_json = lambda method, url, *a, **k: remote_response
applied = bridge.pull_and_apply(
    project,
    'https://ppt-master-hosted.example',
    '2' * 48,
)
assert applied['harness_status'] == 'accepted-by-local-official-confirm-ui'
assert applied['applied_capture_count'] == 1
result = json.loads((project / 'confirm_ui/result.json').read_text(encoding='utf-8'))
assert result['status'] == 'stage1-confirmed'
print(json.dumps({'opened': opened, 'applied': applied}))
""".lstrip(),
        encoding="utf-8",
    )
    proc = run_no_site(probe, runtime, project)
    probe_result = json.loads(proc.stdout)
    assert probe_result["opened"]["active_stage"] == "stage1"
    assert probe_result["applied"]["applied_capture_count"] == 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ppt-master-runtime-headless-") as temp:
        base = Path(temp)
        bundle = base / "runtime.zip"
        subprocess.run(
            [
                PY,
                str(ROOT / "studio/scripts/build_runtime_bundle.py"),
                "--repo-root",
                str(ROOT),
                "--output",
                str(bundle),
            ],
            check=True,
            text=True,
            capture_output=True,
            timeout=180,
        )
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            unicode_path = "skills/ppt-master/templates/brands/中国电信/templates/design_spec.md"
            assert unicode_path in names
            assert archive.getinfo(unicode_path).flag_bits & 0x800
            assert not any(re.search(r"#U[0-9A-Fa-f]{4}", name) for name in names)
            runtime = base / "runtime"
            archive.extractall(runtime)

        project = base / "handoff-project"
        initialize_project(project)
        handoff_roundtrip(runtime, project)

        bridge_project = base / "bridge-project"
        initialize_project(bridge_project)
        bridge_probe(runtime, bridge_project)

    print("Unicode-safe Runtime + Flask-free Hosted Confirm Stage 1/2: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
