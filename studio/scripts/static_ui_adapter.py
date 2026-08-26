#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
# Ensure repository root is importable when executed by path.
REPO_ROOT=Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))
from studio.static_ui.stage1 import stage1_html
from studio.static_ui.stage2 import stage2_html
from studio.static_ui.review import deck_review_html,motion_review_html
from studio.static_ui.validators import validate_response

def write_surface(project:Path,surface:str)->Path:
    project=project.resolve(); outdir=project/"static_ui"; outdir.mkdir(parents=True,exist_ok=True)
    if surface=="stage1": text,name=stage1_html(project),"confirm_stage1.html"
    elif surface=="stage2": text,name=stage2_html(project),"confirm_stage2.html"
    elif surface=="deck-review": text,name=deck_review_html(project),"deck_review.html"
    elif surface=="motion-review": text,name=motion_review_html(project),"motion_review.html"
    else: raise ValueError(f"unknown surface: {surface}")
    out=outdir/name; out.write_text(text,encoding="utf-8"); return out

def main()->int:
    ap=argparse.ArgumentParser(description="PPT Master ChatGPT Static UI Adapter")
    sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build"); b.add_argument("project",type=Path); b.add_argument("surface",choices=["stage1","stage2","deck-review","motion-review"])
    v=sub.add_parser("validate"); v.add_argument("project",type=Path); v.add_argument("response",help="response JSON file path, or - for stdin")
    args=ap.parse_args()
    try:
        out=write_surface(args.project,args.surface) if args.cmd=="build" else validate_response(args.project.resolve(),args.response)
        print(out); return 0
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 86
if __name__=="__main__": raise SystemExit(main())
