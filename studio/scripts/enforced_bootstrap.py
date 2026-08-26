#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

VERSION_REL = Path('studio/VERSION.json')
REQUIRED = [
    'skills/ppt-master/SKILL.md',
    'skills/ppt-master/workflows/routing.md',
    'skills/ppt-master/scripts/attribution_guard.py',
    'skills/ppt-master/scripts/svg_quality_checker.py',
    'skills/ppt-master/scripts/svg_to_pptx.py',
    'skills/ppt-master/scripts/project_manager.py',
    'studio/VERSION.json',
    'studio/PROJECT_BOOTSTRAP.md',
    'studio/enforcement/PPT_MASTER_AUTHORITY.md',
    'studio/enforcement/PPT_MASTER_WORKFLOW.md',
    'studio/enforcement/PPT_MASTER_TEMPLATE_RULES.md',
    'studio/enforcement/PPT_MASTER_REGRESSION_POLICY.md',
    'studio/enforcement/PPT_MASTER_STATIC_UI_RULES.md',
    'studio/enforcement/PPT_MASTER_RECOVERY_RULES.md',
    'studio/regression/regression_policy.json',
    'studio/scripts/static_ui_adapter.py',
    'studio/scripts/enforced_checkpoint.py',
    'studio/scripts/enforced_preflight.py',
    'studio/scripts/enforced_recovery.py',
]
HEX40 = re.compile(r'^[0-9a-f]{40}$')

def git_head(root: Path) -> str | None:
    try:
        r=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],check=True,capture_output=True,text=True)
        v=r.stdout.strip().lower()
        return v if HEX40.match(v) else None
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser(description='PPT Master Studio GitHub-first bootstrap/self-check')
    ap.add_argument('--repo-root',type=Path,required=True)
    ap.add_argument('--running-commit',required=True)
    ap.add_argument('--json',type=Path)
    args=ap.parse_args(); root=args.repo_root.resolve(); requested=args.running_commit.strip().lower()
    missing=[x for x in REQUIRED if not (root/x).exists()]
    errors=[]
    if not HEX40.match(requested): errors.append('running commit must be a full lowercase 40-hex SHA')
    version={}
    if (root/VERSION_REL).is_file():
        try: version=json.loads((root/VERSION_REL).read_text(encoding='utf-8'))
        except Exception as exc: errors.append(f'VERSION.json unreadable: {exc}')
    actual=git_head(root)
    if actual and actual != requested: errors.append(f'checkout HEAD {actual} does not match requested commit {requested}')
    if version.get('repository')!='dycm8009/ppt-master-studio': errors.append('VERSION.json repository mismatch')
    if version.get('studio_version')!='3.2.0': errors.append('VERSION.json studio_version mismatch')
    status='passed' if not missing and not errors else 'failed'
    report={'schema':'ppt-master-studio-bootstrap/v1','studio_version':version.get('studio_version','3.2.0'),'upstream_skill_version':version.get('upstream_skill_version','5.0.0'),'repo_root':str(root),'repository':version.get('repository'),'running_commit':requested,'checkout_head':actual,'status':status,'missing':missing,'errors':errors}
    text=json.dumps(report,ensure_ascii=False,indent=2); print(text)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True); args.json.write_text(text+'\n',encoding='utf-8')
    raise SystemExit(0 if status=='passed' else 86)
if __name__=='__main__': main()
