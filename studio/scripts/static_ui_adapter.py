#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repository root is importable when executed by path.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from studio.static_ui.review import deck_review_html, motion_review_html
from studio.static_ui.stage1 import stage1_html
from studio.static_ui.stage2 import stage2_html
from studio.static_ui.validators import validate_response

SURFACE_BASENAMES = {
    "stage1": "confirm_stage1",
    "stage2": "confirm_stage2",
    "deck-review": "deck_review",
    "motion-review": "motion_review",
}
LEGACY_NAMES = {
    "stage1": "confirm_stage1.html",
    "stage2": "confirm_stage2.html",
    "deck-review": "deck_review.html",
    "motion-review": "motion_review.html",
}
# Keep enough recent revisions for quick comparison while bounding Deck Review growth.
HISTORY_LIMIT = 4
LATEST_MANIFEST = "latest.json"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render_surface(project: Path, surface: str) -> str:
    if surface == "stage1":
        return stage1_html(project)
    if surface == "stage2":
        return stage2_html(project)
    if surface == "deck-review":
        return deck_review_html(project)
    if surface == "motion-review":
        return motion_review_html(project)
    raise ValueError(f"unknown surface: {surface}")


def _load_latest(outdir: Path) -> dict:
    path = outdir / LATEST_MANIFEST
    if not path.is_file():
        return {"schema": "ppt-master-static-ui-latest/v1", "surfaces": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": "ppt-master-static-ui-latest/v1", "surfaces": {}}
    if not isinstance(data, dict) or data.get("schema") != "ppt-master-static-ui-latest/v1":
        return {"schema": "ppt-master-static-ui-latest/v1", "surfaces": {}}
    if not isinstance(data.get("surfaces"), dict):
        data["surfaces"] = {}
    return data


def _write_latest(outdir: Path, data: dict) -> None:
    path = outdir / LATEST_MANIFEST
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _prune_history(outdir: Path, surface: str, keep: int = HISTORY_LIMIT) -> list[str]:
    base = SURFACE_BASENAMES[surface]
    files = sorted(outdir.glob(f"{base}__*.html"), key=lambda p: p.name, reverse=True)
    removed = []
    for old in files[keep:]:
        old.unlink(missing_ok=True)
        removed.append(old.name)
    return removed


def write_surface(project: Path, surface: str) -> Path:
    project = project.resolve()
    outdir = project / "static_ui"
    outdir.mkdir(parents=True, exist_ok=True)

    raw = _render_surface(project, surface)
    generated_at = datetime.now(timezone.utc)
    stamp = generated_at.strftime("%Y%m%dT%H%M%S%fZ")
    content_sha = _sha256_text(raw)
    build_id = f"{stamp}-{content_sha[:12]}"
    base = SURFACE_BASENAMES[surface]
    name = f"{base}__{build_id}.html"

    marker = (
        f"<!-- PPT Master Static UI | surface={surface} | build={build_id} "
        f"| source_html_sha256={content_sha} -->\n"
    )
    text = marker + raw
    html_sha = _sha256_text(text)

    out = outdir / name
    out.write_text(text, encoding="utf-8")

    # Remove the pre-v3.2.2 fixed-name alias. A stale fixed path is more dangerous
    # than a broken old link because it can silently present obsolete confirmation UI.
    legacy = outdir / LEGACY_NAMES[surface]
    legacy_removed = legacy.exists()
    if legacy_removed:
        legacy.unlink()

    latest = _load_latest(outdir)
    latest["updated_at"] = generated_at.isoformat()
    latest["surfaces"][surface] = {
        "file": name,
        "build_id": build_id,
        "generated_at": generated_at.isoformat(),
        "content_sha256": content_sha,
        "html_sha256": html_sha,
        "legacy_fixed_name": LEGACY_NAMES[surface],
        "legacy_fixed_name_removed": legacy_removed,
    }
    _write_latest(outdir, latest)
    _prune_history(outdir, surface)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="PPT Master ChatGPT Static UI Adapter")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("project", type=Path)
    b.add_argument("surface", choices=["stage1", "stage2", "deck-review", "motion-review"])
    v = sub.add_parser("validate")
    v.add_argument("project", type=Path)
    v.add_argument("response", help="response JSON file path, or - for stdin")
    args = ap.parse_args()
    try:
        out = write_surface(args.project, args.surface) if args.cmd == "build" else validate_response(args.project.resolve(), args.response)
        print(out)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 86


if __name__ == "__main__":
    raise SystemExit(main())
