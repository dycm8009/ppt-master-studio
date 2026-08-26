#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone

PHASES=['intake','strategist','deck-art-direction','visual-carrier','authoring','motion','qa','export','complete']
SURFACES=['official-ui','static-html','chat','delegated']
HEX40=re.compile(r'^[0-9a-f]{40}$')
CURRENT='3.2.0'

def load(p:Path):
    if not p.exists(): return {}
    return json.loads(p.read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser(description='Create/update PPT Master Studio project checkpoint')
    ap.add_argument('project',type=Path)
    ap.add_argument('--phase',choices=PHASES,default='intake')
    ap.add_argument('--route',default=None); ap.add_argument('--template',default=None)
    ap.add_argument('--slide-count',type=int,default=None); ap.add_argument('--note',default=None)
    ap.add_argument('--confirmation-surface',choices=SURFACES,default=None)
    ap.add_argument('--harness-repo',default=None)
    ap.add_argument('--harness-ref',default=None)
    ap.add_argument('--harness-commit',default=None)
    args=ap.parse_args(); project=args.project.resolve(); project.mkdir(parents=True,exist_ok=True)
    p=project/'project_state.json'; state=load(p)
    existing_h=state.get('harness') if isinstance(state.get('harness'),dict) else {}
    repo=args.harness_repo or existing_h.get('repo')
    ref=args.harness_ref or existing_h.get('ref')
    commit=(args.harness_commit or existing_h.get('commit') or '').lower()
    if not repo or not ref or not HEX40.match(commit):
        raise SystemExit('harness binding required: --harness-repo, --harness-ref, and full --harness-commit on first checkpoint')
    state['schema']='ppt-master-studio-project-state/v1'
    state['enforced_version']=CURRENT; state['upstream_version']='5.0.0'; state['phase']=args.phase
    state['harness']={'repo':repo,'ref':ref,'commit':commit}
    if args.route is not None: state['route']=args.route
    if args.template is not None: state['template']=args.template
    if args.slide_count is not None: state['slide_count']=args.slide_count
    if args.confirmation_surface is not None: state['confirmation_surface']=args.confirmation_surface
    if args.note: state.setdefault('notes',[]).append(args.note)
    state['updated_at']=datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(p)
if __name__=='__main__': main()
