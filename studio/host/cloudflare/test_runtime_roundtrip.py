#!/usr/bin/env python3
"""End-to-end Runtime round-trip against the deployed dev Worker.

This combines the two separately validated halves:
1. the unmodified official SVG Editor frontend contract on Cloudflare; and
2. the pinned local Harness SVG Editor server as the filesystem authority.

Browser mutations are simulated through the same official /api/* surface after
establishing the editor cookie.  The runtime bridge must then pull the capture,
replay it through the local official server, persist svg_output, and resync the
remote mirror.
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
from urllib.request import HTTPCookieProcessor, Request, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import hosted_editor_bridge as bridge  # noqa: E402


BASE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <rect id="bg" width="1600" height="900" fill="#0B0D12"/>
  <rect id="box" x="120" y="140" width="1360" height="620" fill="#171B24"/>
  <text id="title" x="190" y="300" fill="#F4F7FB" font-size="64" font-family="Arial">Runtime baseline</text>
  <text id="body" x="190" y="400" fill="#C9D2DF" font-size="30" font-family="Arial">Cloudflare is only the interaction mirror.</text>
</svg>
"""


def browser_json(opener, method: str, url: str, body=None):
    data = None
    headers = {"Accept": "application/json", "User-Agent": bridge.HOST_USER_AGENT}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    with opener.open(request, timeout=30) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def shutdown_local(project: Path) -> None:
    server = ROOT / "skills" / "ppt-master" / "scripts" / "svg_editor" / "server.py"
    subprocess.run(
        [sys.executable, str(server), str(project), "--shutdown"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )


def main() -> int:
    remote_base = os.environ.get(
        "PPT_MASTER_HOSTED_DEV_BASE",
        "https://ppt-master-hosted-confirm-dev.dycm-lab.workers.dev",
    ).rstrip("/")
    harness_commit = os.environ.get("PPT_MASTER_HARNESS_COMMIT", "7498ba4719510841a3158409d2bfb4261870e4ae")
    session = secrets.token_hex(24)
    host_key = secrets.token_hex(32)

    with tempfile.TemporaryDirectory(prefix="ppt-master-hosted-roundtrip-") as temp:
        project = Path(temp) / "project"
        svg_output = project / "svg_output"
        svg_output.mkdir(parents=True)
        slide = svg_output / "slide_01.svg"
        slide.write_text(BASE_SVG, encoding="utf-8")

        try:
            opened = bridge.open_hosted_editor(
                project,
                remote_base,
                harness_commit,
                session=session,
                host_key=host_key,
            )
            if opened.get("session") != session:
                raise RuntimeError("runtime bridge replaced the host-known editor session")

            jar = http.cookiejar.CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))
            opener.addheaders = [("User-Agent", bridge.HOST_USER_AGENT)]
            page_request = Request(
                f"{remote_base}/e/{session}",
                headers={"User-Agent": bridge.HOST_USER_AGENT},
            )
            with opener.open(page_request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"Hosted Editor page status {response.status}")

            before = browser_json(opener, "GET", f"{remote_base}/api/slide/slide_01.svg")
            if "Runtime baseline" not in before.get("content", ""):
                raise RuntimeError("remote mirror did not receive the Runtime SVG")

            edited = browser_json(
                opener,
                "POST",
                f"{remote_base}/api/slide/slide_01.svg/edit",
                {"element_id": "title", "text": "Runtime round-trip applied", "attrs": {"fill": "#E66C63"}},
            )
            if edited.get("status") != "ok":
                raise RuntimeError(f"official edit API failed: {edited}")

            annotated = browser_json(
                opener,
                "POST",
                f"{remote_base}/api/slide/slide_01.svg/annotate",
                {"element_id": "box", "annotation": "AI: tighten the visual hierarchy of this region"},
            )
            if annotated.get("status") != "ok":
                raise RuntimeError(f"official annotation API failed: {annotated}")

            captured = browser_json(opener, "POST", f"{remote_base}/api/save-all")
            if captured.get("hosted_status") != "captured-not-applied":
                raise RuntimeError(f"Cloudflare layer crossed authority boundary: {captured}")

            result = bridge.pull_and_apply(
                project,
                remote_base,
                session,
                host_key,
                resync=True,
            )
            if result.get("applied_capture_count") != 1:
                raise RuntimeError(f"capture was not applied exactly once: {result}")
            if result.get("harness_status") != "applied-by-local-official-svg-editor":
                raise RuntimeError(f"local Harness authority was not used: {result}")

            local_svg = slide.read_text(encoding="utf-8")
            if "Runtime round-trip applied" not in local_svg or "#E66C63" not in local_svg:
                raise RuntimeError("direct edit did not persist into local svg_output")
            if 'data-edit-target="true"' not in local_svg or "tighten the visual hierarchy" not in local_svg:
                raise RuntimeError("annotation did not persist into local svg_output")

            after = browser_json(opener, "GET", f"{remote_base}/api/slide/slide_01.svg")
            if "Runtime round-trip applied" not in after.get("content", ""):
                raise RuntimeError("local Harness result was not resynced to Hosted Editor")

            second = bridge.pull_and_apply(
                project,
                remote_base,
                session,
                host_key,
                resync=True,
            )
            if second.get("harness_status") != "no-new-capture" or second.get("applied_capture_count") != 1:
                raise RuntimeError(f"capture cursor is not idempotent: {second}")

            closed = browser_json(
                opener,
                "POST",
                f"{remote_base}/api/shutdown",
                {"reason": "roundtrip-ci-complete"},
            )
            if closed.get("status") != "ok":
                raise RuntimeError(f"Hosted Editor close failed: {closed}")
        finally:
            shutdown_local(project)

    print("hosted official SVG Editor Runtime round-trip: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
