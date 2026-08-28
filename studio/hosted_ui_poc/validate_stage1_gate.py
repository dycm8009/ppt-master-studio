#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.static_ui.base import digest, read_json
from studio.static_ui.templates import build_template_options


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_json(method: str, url: str, body: dict | None = None) -> tuple[int, dict, object]:
    raw = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"accept": "application/json"}
    if raw is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return resp.status, payload, resp.headers
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text)
        except Exception:
            payload = {"error": text}
        raise RuntimeError(f"HTTP {exc.code} {url}: {payload}") from exc


def assert_no_store(headers: object) -> None:
    value = str(headers.get("cache-control", ""))  # type: ignore[attr-defined]
    if "no-store" not in value.lower():
        raise RuntimeError(f"Hosted API response missing Cache-Control: no-store ({value!r})")


def prepare_project(project: Path) -> tuple[dict, dict]:
    confirm = project / "confirm_ui"
    rec_path = confirm / "recommendations.stage1.json"
    opts_path = confirm / "template_options.json"

    if rec_path.is_file() or opts_path.is_file():
        if not rec_path.is_file() or not opts_path.is_file():
            raise RuntimeError("project must contain both confirm_ui/recommendations.stage1.json and confirm_ui/template_options.json")
        rec = read_json(rec_path)
    else:
        rec = {
            "stage": "stage1",
            "primary_language": "zh-CN",
            "audience": "AI 工程师和开发者",
            "communication_intent": "分享 AI Agent Skills 的实践经验",
            "audience_outcome": "理解如何设计和使用 Skills",
            "core_message": "Skills 是 Agent 能力工程化的重要抽象",
            "delivery_context": "技术分享",
            "artifact_afterlife": "会后参考材料",
            "content_divergence": "保持核心内容，允许表达优化",
            "recommend": {"canvas": "ppt169"},
        }
        source_options = {
            "schema_version": 1,
            "phase": "template",
            "default_mode": "free_design",
            "lang": "zh-CN",
            "explicit_workspace_roots": [],
        }
        write_json(rec_path, rec)
        write_json(opts_path, source_options)

    if rec.get("stage") != "stage1":
        raise RuntimeError("recommendations.stage1.json must declare stage=stage1")

    options, _ = build_template_options(project)
    payload = {
        "recommendation_sha256": digest(rec),
        "options_sha256": options["options_sha256"],
        "recommendation": rec,
    }
    return rec, payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Real Cloudflare Hosted Stage 1 -> local Harness validation gate")
    ap.add_argument("--base-url", required=True, help="deployed Worker origin, e.g. https://name.account.workers.dev")
    ap.add_argument("--project", type=Path, help="existing Stage 1 project; omit to create a real scratch project")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")
    project = args.project.resolve() if args.project else Path(tempfile.mkdtemp(prefix="ppt-master-hosted-stage1-gate-"))
    project.mkdir(parents=True, exist_ok=True)
    _rec, payload = prepare_project(project)

    status, created, headers = request_json("POST", f"{base_url}/api/sessions", {"surface": "stage1", "payload": payload})
    assert_no_store(headers)
    if status != 201:
        raise RuntimeError(f"expected 201 creating session, got {status}")
    token = str(created.get("session", ""))
    if len(token) != 48:
        raise RuntimeError(f"unexpected session token: {token!r}")

    status, session, headers = request_json("GET", f"{base_url}/api/sessions/{token}")
    assert_no_store(headers)
    if status != 200 or session.get("status") != "open":
        raise RuntimeError(f"immediate session read failed: {status} {session}")
    if session.get("payload") != payload:
        raise RuntimeError("immediate session payload differs from the project-derived payload")

    browser_url = f"{base_url}/s/{token}"
    print("HOSTED TRANSPORT PRE-CAPTURE: PASS")
    print(f"project: {project}")
    print(f"browser: {browser_url}")
    print(f"expires_at: {created.get('expires_at')}")
    input("Open the browser URL, click '确认并捕获', then press Enter here to continue... ")

    status, captured, headers = request_json("GET", f"{base_url}/api/sessions/{token}/response")
    assert_no_store(headers)
    if status != 200 or captured.get("schema") != "ppt-master-hosted-captured/v1":
        raise RuntimeError(f"captured response fetch failed: {status} {captured}")
    response = captured.get("response")
    if not isinstance(response, dict) or response.get("status") != "user-confirmed":
        raise RuntimeError(f"unexpected hosted response: {response}")

    response_path = project / "static_ui" / "hosted_response.stage1.json"
    write_json(response_path, response)
    validator = ROOT / "studio" / "scripts" / "static_ui_adapter.py"
    proc = subprocess.run(
        [sys.executable, str(validator), "validate", str(project), str(response_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Harness validation failed\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")

    accepted_path = project / "static_ui" / "accepted.stage1.json"
    accepted = read_json(accepted_path)
    if accepted.get("schema") != "ppt-master-static-ui-accepted/v1" or accepted.get("status") != "accepted":
        raise RuntimeError(f"unexpected accepted receipt: {accepted}")
    if accepted.get("recommendation_sha256") != payload["recommendation_sha256"]:
        raise RuntimeError("accepted recommendation hash differs from hosted project payload")
    if accepted.get("options_sha256") != payload["options_sha256"]:
        raise RuntimeError("accepted options hash differs from hosted project payload")

    print("HOSTED RESPONSE ROUND-TRIP: PASS")
    print("LOCAL HARNESS VALIDATION: PASS")
    print(f"accepted: {accepted_path}")
    print(json.dumps(accepted, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
