#!/usr/bin/env python3
"""Build the commit-bound PPT Master Studio Runtime ZIP safely.

The prior shell ``zip`` packaging path rewrote non-ASCII path names into
``#Uxxxx`` escapes on the GitHub runner.  Python's ``zipfile`` module emits the
ZIP UTF-8 filename flag, so template library paths remain byte-for-byte usable
when the artifact is extracted by ChatGPT hosts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import zipfile

RUNTIME_INPUTS = (
    "skills/ppt-master",
    "studio/VERSION.json",
    "studio/host/chatgpt/ENTRYPOINT.md",
    "studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md",
    "studio/scripts/enforced_bootstrap.py",
    "studio/scripts/enforced_checkpoint.py",
    "studio/scripts/enforced_preflight.py",
    "studio/scripts/enforced_recovery.py",
    "studio/host/cloudflare/HOSTED_UI.json",
    "studio/host/cloudflare/hosted_url.py",
    "studio/host/cloudflare/hosted_confirm_handoff.py",
    "studio/host/cloudflare/hosted_confirm_bridge.py",
    "studio/host/cloudflare/hosted_editor_bridge.py",
)

IGNORED_NAMES = {"__pycache__", ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def _files_for(root: Path, relative: str) -> list[Path]:
    source = root / relative
    if not source.exists():
        raise FileNotFoundError(f"runtime input missing: {relative}")
    if source.is_file():
        return [source]
    return sorted(
        (path for path in source.rglob("*") if path.is_file() and not _ignored(path.relative_to(root))),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _zip_info(source: Path, arcname: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(arcname, FIXED_TIMESTAMP)
    info.create_system = 3
    mode = stat.S_IMODE(source.stat().st_mode)
    info.external_attr = ((stat.S_IFREG | mode) & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    # ZipFile encodes non-ASCII str names as UTF-8 and sets bit 11 on write.
    return info


def build_runtime_bundle(repo_root: Path, output: Path) -> dict[str, object]:
    root = repo_root.resolve()
    destination = output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".tmp")
    temp.unlink(missing_ok=True)

    files: list[Path] = []
    for relative in RUNTIME_INPUTS:
        files.extend(_files_for(root, relative))

    names: set[str] = set()
    unicode_names = 0
    total_bytes = 0
    with zipfile.ZipFile(
        temp,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        allowZip64=True,
    ) as archive:
        for source in files:
            arcname = source.relative_to(root).as_posix()
            if arcname in names:
                raise RuntimeError(f"duplicate runtime archive path: {arcname}")
            names.add(arcname)
            if not arcname.isascii():
                unicode_names += 1
            data = source.read_bytes()
            total_bytes += len(data)
            archive.writestr(_zip_info(source, arcname), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    os.replace(temp, destination)
    report = {
        "schema": "ppt-master-studio-runtime-bundle/v1",
        "output": str(destination),
        "file_count": len(names),
        "unicode_path_count": unicode_names,
        "uncompressed_bytes": total_bytes,
        "archive_bytes": destination.stat().st_size,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Unicode-safe PPT Master Studio Runtime ZIP")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_runtime_bundle(args.repo_root, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
