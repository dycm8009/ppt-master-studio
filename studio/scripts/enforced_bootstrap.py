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
    'studio/CHATGPT_PROJECT_INSTRUCTIONS.txt',
    'studio/enforcement/PPT_MASTER_AUTHORITY.md',
    'studio/enforcement/PPT_MASTER_WORKFLOW.md',
    'studio/enforcement/PPT_MASTER_TEMPLATE_RULES.md',
    'studio/enforcement/PPT_MASTER_REGRESSION_POLICY.md',
    'studio/enforcement/PPT_MASTER_STATIC_UI_RULES.md',
    'studio/enforcement/PPT_MASTER_RECOVERY_RULES.md',
    'studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md',
    'studio/regression/regression_policy.json',
    'studio/scripts/static_ui_adapter.py',
    'studio/scripts/enforced_checkpoint.py',
    'studio/scripts/enforced_preflight.py',
    'studio/scripts/enforced_recovery.py',
]
HEX40 = re.compile(r'^[0-9a-f]{40}$')
STUDIO_VERSION = '3.2.3'
PROJECT_CONTRACT_VERSION = '3.2.0'

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
    if version.get('studio_version')!=STUDIO_VERSION: errors.append('VERSION.json studio_version mismatch')
    if version.get('project_contract_version')!=PROJECT_CONTRACT_VERSION: errors.append('VERSION.json project_contract_version mismatch')
    if int(version.get('host_bootstrap_revision') or 0) < 3: errors.append('VERSION.json host_bootstrap_revision must be >= 3')
    if version.get('container_network_fallback_forbidden') is not True: errors.append('VERSION.json must forbid container network fallback')
    if int(version.get('static_ui_revision') or 0) < 2: errors.append('VERSION.json static_ui_revision must be >= 2')
    if version.get('runtime_release_tag_pattern')!='studio-runtime-{commit}': errors.append('VERSION.json runtime release tag pattern mismatch')
    if version.get('runtime_release_asset_pattern')!='ppt-master-studio-runtime-{commit}.zip': errors.append('VERSION.json runtime release asset pattern mismatch')
    status='passed' if not missing and not errors else 'failed'
    report={'schema':'ppt-master-studio-bootstrap/v1','studio_version':version.get('studio_version',STUDIO_VERSION),'project_contract_version':version.get('project_contract_version',PROJECT_CONTRACT_VERSION),'upstream_skill_version':version.get('upstream_skill_version','5.0.0'),'repo_root':str(root),'repository':version.get('repository'),'running_commit':requested,'checkout_head':actual,'host_bootstrap_revision':version.get('host_bootstrap_revision'),'container_network_fallback_forbidden':version.get('container_network_fallback_forbidden'),'static_ui_revision':version.get('static_ui_revision'),'status':status,'missing':missing,'errors':errors}
    text=json.dumps(report,ensure_ascii=False,indent=2); print(text)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True); args.json.write_text(text+'\n',encoding='utf-8')
    raise SystemExit(0 if status=='passed' else 86)
if __name__=='__main__': main()
