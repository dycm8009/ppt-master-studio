#!/usr/bin/env python3
"""Deployed Hosted Confirm UI -> local pinned official Confirm UI round-trip.

The test uses the same remote /api/confirm surface as the official browser app,
then requires ``hosted_confirm_bridge.py`` to replay each capture unchanged into
local ``confirm_ui/server.py``.  Stage 1 receipts, template handoff and final
Stage 2 result must therefore be created by the pinned official Harness, never
by Cloudflare.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.request import HTTPCookieProcessor, Request, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import hosted_confirm_bridge as bridge  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def browser_json(opener, method: str, url: str, body=None):
    data = None
    headers = {"Accept": "application/json", "User-Agent": bridge.HOST_USER_AGENT}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    with opener.open(Request(url, data=data, method=method, headers=headers), timeout=30) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def stage1_recommendation() -> dict:
    return {
        "stage": "stage1",
        "lang": "zh",
        "primary_language": "zh-CN",
        "recommend": {"canvas": "ppt169"},
        "audience": {"value": "研发团队"},
        "communication_intent": {"value": "形成工程决策共识"},
        "audience_outcome": {"value": "理解架构边界与下一步"},
        "core_message": {"value": "证据驱动架构决策"},
        "delivery_context": {"value": "20 分钟技术分享"},
        "artifact_afterlife": {"value": "设计评审参考"},
        "content_divergence": {"value": ""},
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


def main() -> int:
    remote_base = os.environ.get(
        "PPT_MASTER_HOSTED_DEV_BASE",
        "https://ppt-master-hosted-confirm-dev.dycm-lab.workers.dev",
    ).rstrip("/")
    harness_commit = os.environ.get(
        "PPT_MASTER_HARNESS_COMMIT",
        "7498ba4719510841a3158409d2bfb4261870e4ae",
    )
    session = secrets.token_hex(24)
    host_key = secrets.token_hex(32)

    with tempfile.TemporaryDirectory(prefix="ppt-master-hosted-confirm-") as temp:
        project = Path(temp) / "project"
        confirm = project / "confirm_ui"
        confirm.mkdir(parents=True)
        write_json(confirm / "template_options.json", {
            "schema_version": 1,
            "phase": "template",
            "default_mode": "free_design",
            "lang": "zh",
            "explicit_workspace_roots": [],
        })
        write_json(confirm / "recommendations.stage1.json", stage1_recommendation())

        try:
            opened = bridge.open_hosted_confirm(
                project,
                harness_commit,
                remote_base=remote_base,
                session=session,
                host_key=host_key,
            )
            if opened.get("active_stage") != "stage1" or opened.get("session") != session:
                raise RuntimeError(f"Hosted Confirm Stage 1 open failed: {opened}")

            jar = http.cookiejar.CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))
            opener.addheaders = [("User-Agent", bridge.HOST_USER_AGENT)]
            with opener.open(Request(f"{remote_base}/s/{session}", headers={"User-Agent": bridge.HOST_USER_AGENT}), timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"Hosted Confirm page status {response.status}")

            stage1_payload = {
                "stage": "stage1",
                "primary_language": "zh-CN",
                "canvas": "ppt169",
                "audience": "研发团队",
                "communication_intent": "形成工程决策共识",
                "audience_outcome": "理解架构边界与下一步",
                "core_message": "证据驱动架构决策",
                "delivery_context": "20 分钟技术分享",
                "artifact_afterlife": "设计评审参考",
                "content_divergence": "",
                "template_selection": {"mode": "free_design", "selection_keys": []},
            }
            captured1 = browser_json(opener, "POST", f"{remote_base}/api/confirm", stage1_payload)
            if captured1.get("status") != "captured-not-validated":
                raise RuntimeError(f"remote Stage 1 crossed authority boundary: {captured1}")
            applied1 = bridge.pull_and_apply(project, remote_base, session)
            if applied1.get("harness_status") != "accepted-by-local-official-confirm-ui":
                raise RuntimeError(f"local official Stage 1 was not authority: {applied1}")

            result1 = json.loads((confirm / "result.json").read_text(encoding="utf-8"))
            selection = json.loads((confirm / "template_selection.json").read_text(encoding="utf-8"))
            if result1.get("status") != "stage1-confirmed" or selection.get("mode") != "free_design":
                raise RuntimeError("official Stage 1 receipts were not persisted")

            server = ROOT / "skills" / "ppt-master" / "scripts" / "confirm_ui" / "server.py"
            proc = subprocess.run(
                [sys.executable, str(server), str(project), "--complete-template-selection"],
                text=True,
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"official template handoff failed: {proc.stderr or proc.stdout}")
            time.sleep(0.02)
            write_json(confirm / "recommendations.stage2.json", stage2_recommendation())

            advanced = bridge.advance_stage2(project, remote_base, session, host_key)
            if advanced.get("stage") != "stage2":
                raise RuntimeError(f"Stage 2 remote advance failed: {advanced}")

            captured2 = browser_json(opener, "POST", f"{remote_base}/api/confirm", final_payload())
            if captured2.get("status") != "captured-not-validated":
                raise RuntimeError(f"remote Stage 2 crossed authority boundary: {captured2}")
            applied2 = bridge.pull_and_apply(project, remote_base, session)
            if applied2.get("harness_status") != "accepted-by-local-official-confirm-ui":
                raise RuntimeError(f"local official Stage 2 was not authority: {applied2}")
            if applied2.get("applied_capture_count") != 2:
                raise RuntimeError(f"capture cursor mismatch: {applied2}")

            result2 = json.loads((confirm / "result.json").read_text(encoding="utf-8"))
            if result2.get("stage") != "final" or result2.get("status") != "confirmed":
                raise RuntimeError("official final Stage 2 receipt was not persisted")

            again = bridge.pull_and_apply(project, remote_base, session)
            if again.get("harness_status") != "no-new-capture" or again.get("applied_capture_count") != 2:
                raise RuntimeError(f"Hosted Confirm capture cursor is not idempotent: {again}")

            # Dev Worker keeps acceptance helpers; close through the browser API.
            closed = browser_json(opener, "POST", f"{remote_base}/api/shutdown", {"reason": "confirm-roundtrip-ci"})
            if closed.get("status") != "closed":
                raise RuntimeError(f"Hosted Confirm browser close failed: {closed}")
        finally:
            bridge.shutdown_local_confirm_server(project)

    print("hosted official Confirm UI Runtime round-trip: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
