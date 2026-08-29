#!/usr/bin/env python3
"""Deployed Cloudflare Stage 1/2 round-trip using the browser copy-JSON contract."""
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
from test_confirm_runtime_roundtrip import (  # noqa: E402
    browser_json,
    final_payload,
    stage1_recommendation,
    stage2_recommendation,
    write_json,
)


def stage1_payload() -> dict:
    return {
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


def copied_return(session: str, stage: str, response: dict) -> dict:
    return {
        "schema": "ppt-master-hosted-confirm-return/v1",
        "session": session,
        "stage": stage,
        "response": response,
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

    with tempfile.TemporaryDirectory(prefix="ppt-master-hosted-return-") as temp:
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

        opened = bridge.open_hosted_confirm(
            project,
            harness_commit,
            remote_base=remote_base,
            session=session,
            host_key=host_key,
        )
        expected_url = f"{remote_base}/s/{session}"
        if opened.get("launch_url") != expected_url or opened.get("session_url") != expected_url:
            raise RuntimeError(f"direct session launch contract failed: {opened}")

        jar = http.cookiejar.CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        opener.addheaders = [("User-Agent", bridge.HOST_USER_AGENT)]
        with opener.open(
            Request(expected_url, headers={"User-Agent": bridge.HOST_USER_AGENT}), timeout=30
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Hosted Confirm page status {response.status}")

        captured1 = browser_json(opener, "POST", f"{remote_base}/api/confirm", stage1_payload())
        if captured1.get("status") != "captured-not-validated":
            raise RuntimeError(f"remote Stage 1 capture failed: {captured1}")
        response1 = browser_json(
            opener, "GET", f"{remote_base}/api/sessions/{session}/response"
        )
        applied1 = bridge.apply_return(project, copied_return(session, "stage1", response1))
        if applied1.get("harness_status") != "accepted-by-local-official-confirm-ui":
            raise RuntimeError(f"copied Stage 1 return was not accepted: {applied1}")

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
        if advanced.get("stage") != "stage2" or advanced.get("launch_url") != expected_url:
            raise RuntimeError(f"Stage 2 direct-session advance failed: {advanced}")

        captured2 = browser_json(opener, "POST", f"{remote_base}/api/confirm", final_payload())
        if captured2.get("status") != "captured-not-validated":
            raise RuntimeError(f"remote Stage 2 capture failed: {captured2}")
        response2 = browser_json(
            opener, "GET", f"{remote_base}/api/sessions/{session}/response"
        )
        applied2 = bridge.apply_return(project, copied_return(session, "stage2", response2))
        if applied2.get("harness_status") != "accepted-by-local-official-confirm-ui":
            raise RuntimeError(f"copied Stage 2 return was not accepted: {applied2}")
        if applied2.get("applied_capture_count") != 2:
            raise RuntimeError(f"copied return cursor mismatch: {applied2}")

        result = json.loads((confirm / "result.json").read_text(encoding="utf-8"))
        if result.get("stage") != "final" or result.get("status") != "confirmed":
            raise RuntimeError("official final Stage 2 receipt was not persisted")

        closed = browser_json(
            opener, "POST", f"{remote_base}/api/shutdown", {"reason": "manual-return-roundtrip-ci"}
        )
        if closed.get("status") != "closed":
            raise RuntimeError(f"Hosted Confirm close failed: {closed}")

    print("deployed direct launch + copied JSON Stage 1/2 round-trip: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
