#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,zipfile
from pathlib import Path

PHASES=['intake','strategist','deck-art-direction','visual-carrier','authoring','motion','qa','export','complete']
CURRENT='3.2.0'; MANIFEST='PPT_MASTER_RECOVERY_MANIFEST.json'; HEX40=re.compile(r'^[0-9a-f]{40}$')

def recovery_manifests(project:Path):
    out=[]
    for z in sorted((project/'recovery').glob('*.ppt-recovery.zip')) if (project/'recovery').is_dir() else []:
        try:
            with zipfile.ZipFile(z,'r') as f: m=json.loads(f.read(MANIFEST).decode('utf-8'))
            if str(m.get('schema','')).startswith('ppt-master-portable-recovery/'): out.append((z,m))
        except Exception: continue
    return out

def snapshot_contains(manifest:dict,path:str)->bool:
    return any(isinstance(x,dict) and x.get('path')==path for x in manifest.get('files',[]))

def main():
    ap=argparse.ArgumentParser(description='Fail-closed project preflight for PPT Master Studio')
    ap.add_argument('project',type=Path); ap.add_argument('--running-commit',required=True)
    args=ap.parse_args(); p=args.project.resolve(); errs=[]; warns=[]; running=args.running_commit.lower()
    if not HEX40.match(running): errs.append('running commit must be a full 40-hex SHA')
    state_p=p/'project_state.json'
    if not state_p.exists():
        errs.append('project_state.json missing; attempt verified Portable Recovery before preflight')
    else:
        st=json.loads(state_p.read_text(encoding='utf-8'))
        if st.get('enforced_version')!=CURRENT: errs.append(f'project_state enforced_version must be {CURRENT}; run an explicit migration, do not auto-upgrade')
        h=st.get('harness') if isinstance(st.get('harness'),dict) else {}
        commit=str(h.get('commit') or '').lower()
        if not h.get('repo') or not h.get('ref') or not HEX40.match(commit): errs.append('project_state harness binding missing/invalid')
        elif commit != running: errs.append(f'running Harness commit {running} does not match project pin {commit}')
        n=int(st.get('slide_count') or 0); phase=st.get('phase','intake'); rank={x:i for i,x in enumerate(PHASES)}; r=rank.get(phase,0)
        surface=st.get('confirmation_surface'); recovs=recovery_manifests(p)
        if r>=rank['authoring']:
            for req in ['design_spec.md','spec_lock.md']:
                if not (p/req).exists(): errs.append(f'{req} missing before authoring')
            if n>=18 and not (p/'deck_plan.json').exists(): errs.append('deck_plan.json missing for long deck')
            if surface=='static-html':
                for req in ['static_ui/accepted.stage1.json','static_ui/accepted.stage2.json']:
                    if not (p/req).exists(): errs.append(f'{req} missing for static-html confirmation')
            if not recovs: errs.append('portable recovery snapshot missing before authoring')
        if r>=rank['qa']:
            if not (p/'validation').exists(): errs.append('validation/ missing before QA/export')
            if surface=='static-html' and not (p/'static_ui/accepted.deck-review.json').exists(): errs.append('static_ui/accepted.deck-review.json missing before QA/export')
            if recovs and surface=='static-html' and not any(snapshot_contains(m,'static_ui/accepted.deck-review.json') for _,m in recovs): errs.append('no portable recovery snapshot contains accepted Deck Review')
        if r>=rank['export'] and surface=='static-html' and (p/'motion_budget_plan.json').exists():
            if not (p/'static_ui/accepted.motion-review.json').exists(): errs.append('static_ui/accepted.motion-review.json missing for active motion review')
            if recovs and not any(snapshot_contains(m,'static_ui/accepted.motion-review.json') for _,m in recovs): errs.append('no portable recovery snapshot contains accepted Motion Review')
    status='passed' if not errs else 'failed'
    print(json.dumps({'schema':'ppt-master-studio-preflight/v1','studio_version':CURRENT,'status':status,'errors':errs,'warnings':warns},ensure_ascii=False,indent=2))
    raise SystemExit(0 if not errs else 86)
if __name__=='__main__': main()
