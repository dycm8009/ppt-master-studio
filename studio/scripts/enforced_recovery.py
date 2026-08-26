#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ENFORCED_VERSION = "3.2.0"
UPSTREAM_VERSION = "5.0.0"
MANIFEST_NAME = "PPT_MASTER_RECOVERY_MANIFEST.json"
SCHEMA = "ppt-master-portable-recovery/v2"

EXCLUDED_TOP_LEVEL = {"recovery", "exports", "live_preview", ".confirm_ui.lock", ".live_preview.lock"}
EXCLUDED_SUFFIXES = {".pyc"}
EXCLUDED_DIR_NAMES = {"__pycache__", ".DS_Store"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(name: str) -> Path:
    pp = PurePosixPath(name)
    if pp.is_absolute() or ".." in pp.parts or not pp.parts:
        raise ValueError(f"unsafe archive path: {name}")
    return Path(*pp.parts)


def state_for(project: Path) -> dict:
    p = project / "project_state.json"
    if not p.is_file():
        raise ValueError("project_state.json missing; cannot create authoritative recovery snapshot")
    st = json.loads(p.read_text(encoding="utf-8"))
    if st.get("enforced_version") != ENFORCED_VERSION:
        raise ValueError(f"project_state must be explicitly migrated to {ENFORCED_VERSION} before snapshot")
    h = st.get("harness") if isinstance(st.get("harness"), dict) else {}
    commit = str(h.get("commit") or "").lower()
    if not h.get("repo") or not h.get("ref") or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("project_state harness binding missing/invalid")
    return st


def eligible_dirs(project: Path):
    for p in sorted(project.rglob("*")):
        if not p.is_dir() or p.is_symlink():
            continue
        rel = p.relative_to(project)
        if rel.parts[0] in EXCLUDED_TOP_LEVEL or any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
            continue
        yield rel


def eligible_files(project: Path):
    for p in sorted(project.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(project)
        if rel.parts[0] in EXCLUDED_TOP_LEVEL or any(part in EXCLUDED_DIR_NAMES for part in rel.parts) or p.suffix in EXCLUDED_SUFFIXES:
            continue
        yield p, rel


def snapshot(project: Path, output: Path | None, label: str | None) -> Path:
    project = project.resolve(); st = state_for(project); phase = str(st.get("phase") or "unknown")
    now = datetime.now(timezone.utc); stamp = now.strftime("%Y%m%dT%H%M%SZ")
    safe_label = "" if not label else "__" + "".join(c if c.isalnum() or c in "-_" else "-" for c in label)[:48]
    if output is None:
        outdir = project / "recovery"; outdir.mkdir(parents=True, exist_ok=True)
        output = outdir / f"{project.name}__{phase}{safe_label}__{stamp}.ppt-recovery.zip"
    else:
        output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    directories = [rel.as_posix() for rel in eligible_dirs(project)]
    files = list(eligible_files(project))
    if not files: raise ValueError("project contains no recovery-eligible files")
    for p, rel in files:
        entries.append({"path": rel.as_posix(), "size": p.stat().st_size, "sha256": sha256_file(p)})
    manifest = {
        "schema": SCHEMA, "enforced_version": ENFORCED_VERSION,
        "compatible_project_state_versions": [ENFORCED_VERSION], "upstream_version": UPSTREAM_VERSION,
        "project_name": project.name, "phase": phase, "route": st.get("route"),
        "confirmation_surface": st.get("confirmation_surface"), "slide_count": st.get("slide_count"),
        "harness": st.get("harness"), "label": label, "created_at": now.isoformat(),
        "file_count": len(entries), "directory_count": len(directories), "directories": directories, "files": entries,
    }
    tmp = output.with_suffix(output.suffix + ".tmp")
    if tmp.exists(): tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for rel in directories: zf.writestr(rel.rstrip("/") + "/", b"")
        for p, rel in files: zf.write(p, rel.as_posix())
    os.replace(tmp, output)
    print(json.dumps({"schema":"ppt-master-portable-recovery-snapshot/v1","status":"passed","snapshot":str(output),"phase":phase,"file_count":len(entries),"sha256":sha256_file(output)}, ensure_ascii=False, indent=2))
    return output


def read_manifest(bundle: Path) -> dict:
    bundle = bundle.resolve()
    if not bundle.is_file(): raise ValueError(f"recovery bundle not found: {bundle}")
    if not zipfile.is_zipfile(bundle): raise ValueError("recovery bundle is not a ZIP archive")
    with zipfile.ZipFile(bundle, "r") as zf:
        names = zf.namelist()
        if MANIFEST_NAME not in names: raise ValueError(f"{MANIFEST_NAME} missing")
        manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
    if manifest.get("schema") != SCHEMA: raise ValueError("unsupported recovery manifest schema")
    if manifest.get("enforced_version") != ENFORCED_VERSION: raise ValueError(f"recovery bundle enforced_version is not {ENFORCED_VERSION}")
    h = manifest.get("harness") if isinstance(manifest.get("harness"), dict) else {}
    if not h.get("repo") or not h.get("ref") or not re.fullmatch(r"[0-9a-f]{40}", str(h.get("commit") or "").lower()):
        raise ValueError("recovery manifest harness binding missing/invalid")
    return manifest


def verify(bundle: Path) -> dict:
    manifest = read_manifest(bundle)
    expected = {item["path"]: item for item in manifest.get("files", []) if isinstance(item, dict)}
    for d in manifest.get("directories", []):
        if not isinstance(d, str): raise ValueError("invalid recovery directory entry")
        safe_rel(d)
    if not expected: raise ValueError("recovery manifest contains no files")
    with zipfile.ZipFile(bundle, "r") as zf:
        names = set(zf.namelist())
        for name, item in expected.items():
            safe_rel(name)
            if name not in names: raise ValueError(f"snapshot file missing from archive: {name}")
            raw = zf.read(name); got = hashlib.sha256(raw).hexdigest()
            if got != item.get("sha256"): raise ValueError(f"snapshot checksum mismatch: {name}")
            if len(raw) != int(item.get("size", -1)): raise ValueError(f"snapshot size mismatch: {name}")
    return manifest


def restore(bundle: Path, target: Path, replace: bool) -> Path:
    bundle = bundle.resolve(); manifest = verify(bundle); target = target.resolve()
    if target.exists() and any(target.iterdir()):
        if not replace: raise ValueError(f"restore target is not empty: {target}; pass --replace to restore into it")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppt-recovery-") as td:
        temp = Path(td)
        with zipfile.ZipFile(bundle, "r") as zf:
            for d in manifest.get("directories", []): (temp / safe_rel(d)).mkdir(parents=True, exist_ok=True)
            for item in manifest["files"]:
                rel = safe_rel(item["path"]); dest = temp / rel; dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(item["path"], "r") as src, dest.open("wb") as dst: shutil.copyfileobj(src, dst)
        for item in manifest["files"]:
            p = temp / safe_rel(item["path"])
            if sha256_file(p) != item["sha256"]: raise ValueError(f"post-extract checksum mismatch: {item['path']}")
        for p in sorted(temp.rglob("*")):
            if p.is_dir(): (target / p.relative_to(temp)).mkdir(parents=True, exist_ok=True)
        for p in sorted(temp.rglob("*")):
            if p.is_file():
                rel = p.relative_to(temp); dest = target / rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
    state_path = target / "project_state.json"; st = json.loads(state_path.read_text(encoding="utf-8"))
    st["enforced_version"] = ENFORCED_VERSION; st["upstream_version"] = UPSTREAM_VERSION; st["harness"] = manifest["harness"]
    st.setdefault("recovery", {}).update({"restored_from":bundle.name,"restored_at":datetime.now(timezone.utc).isoformat(),"snapshot_phase":manifest.get("phase"),"snapshot_sha256":sha256_file(bundle)})
    state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    recovery_dir = target / "recovery"; recovery_dir.mkdir(parents=True, exist_ok=True)
    bundle_name = bundle.name if bundle.name.endswith(".ppt-recovery.zip") else f"restored__{manifest.get('phase') or 'unknown'}__{sha256_file(bundle)[:12]}.ppt-recovery.zip"
    restored_bundle = recovery_dir / bundle_name
    if bundle != restored_bundle: shutil.copy2(bundle, restored_bundle)
    print(json.dumps({"schema":"ppt-master-portable-recovery-restore/v1","status":"passed","target":str(target),"phase":manifest.get("phase"),"file_count":manifest.get("file_count"),"bundle_sha256":sha256_file(bundle),"next":f"run enforced_preflight.py {target}"}, ensure_ascii=False, indent=2))
    return target


def salvage_deck_review(html_path: Path, project: Path) -> Path:
    text = html_path.resolve().read_text(encoding="utf-8", errors="strict")
    m = re.search(r'<script id="adapter-data" type="application/json">(.*?)</script>', text, re.S)
    if not m: raise ValueError("deck_review HTML adapter-data block not found")
    data = json.loads(m.group(1))
    if data.get("schema") != "ppt-master-static-deck-review/v1": raise ValueError("HTML is not a supported static Deck Review surface")
    slides = data.get("slides")
    if not isinstance(slides, list) or not slides: raise ValueError("Deck Review contains no embedded slides")
    project = project.resolve(); out = project / "svg_output"; out.mkdir(parents=True, exist_ok=True); written=[]
    for item in slides:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str) or not isinstance(item.get("svg"), str): raise ValueError("invalid embedded slide entry")
        name = Path(item["file"]).name
        if name != item["file"] or not name.lower().endswith(".svg"): raise ValueError(f"unsafe embedded slide filename: {item.get('file')}")
        svg = item["svg"]
        for prefix in ("images/", "icons/", "templates/", "sources/"):
            svg = svg.replace(f'href="../{prefix}', f'href="{prefix}').replace(f"href='../{prefix}", f"href='{prefix}")
        (out / name).write_text(svg.rstrip() + "\n", encoding="utf-8"); written.append(name)
    print(json.dumps({"schema":"ppt-master-deck-review-salvage/v1","status":"partial-salvage","project":str(project),"svg_count":len(written),"files":written,"warning":"SVG markup recovered only; this is not a valid project resume until real specs/state/confirmations/resources are restored and preflight passes."}, ensure_ascii=False, indent=2))
    return project


def main() -> int:
    ap = argparse.ArgumentParser(description="Portable recovery snapshots for PPT Master Studio v3.2.0")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("project", type=Path); s.add_argument("--output", type=Path); s.add_argument("--label")
    i = sub.add_parser("inspect"); i.add_argument("bundle", type=Path)
    r = sub.add_parser("restore"); r.add_argument("bundle", type=Path); r.add_argument("target", type=Path); r.add_argument("--replace", action="store_true")
    d = sub.add_parser("salvage-deck-review"); d.add_argument("html", type=Path); d.add_argument("project", type=Path)
    args = ap.parse_args()
    try:
        if args.cmd == "snapshot": snapshot(args.project, args.output, args.label)
        elif args.cmd == "inspect":
            m = verify(args.bundle)
            print(json.dumps({"schema":"ppt-master-portable-recovery-inspect/v1","status":"passed","bundle":str(args.bundle.resolve()),"bundle_sha256":sha256_file(args.bundle.resolve()),"project_name":m.get("project_name"),"phase":m.get("phase"),"route":m.get("route"),"confirmation_surface":m.get("confirmation_surface"),"slide_count":m.get("slide_count"),"harness":m.get("harness"),"created_at":m.get("created_at"),"file_count":m.get("file_count"),"directory_count":m.get("directory_count")}, ensure_ascii=False, indent=2))
        elif args.cmd == "restore": restore(args.bundle, args.target, args.replace)
        elif args.cmd == "salvage-deck-review": salvage_deck_review(args.html, args.project)
        return 0
    except Exception as exc:
        print(json.dumps({"schema":"ppt-master-portable-recovery-error/v1","status":"failed","error":str(exc)}, ensure_ascii=False, indent=2)); return 86

if __name__ == "__main__": raise SystemExit(main())
