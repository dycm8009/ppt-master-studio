#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PY=sys.executable
SHA=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip().lower()

def run(*args, ok=True):
    p=subprocess.run([PY,*map(str,args)],cwd=ROOT,text=True,capture_output=True)
    if ok and p.returncode!=0:
        raise AssertionError(f'command failed: {args}\nSTDOUT={p.stdout}\nSTDERR={p.stderr}')
    return p

def main():
    v=json.loads((ROOT/'studio/VERSION.json').read_text())
    assert v['studio_version']=='3.2.0'
    run(ROOT/'studio/scripts/enforced_bootstrap.py','--repo-root',ROOT,'--running-commit',SHA)
    with tempfile.TemporaryDirectory() as td:
        base=Path(td); project=base/'project'
        run(ROOT/'studio/scripts/enforced_checkpoint.py',project,'--phase','intake','--harness-repo','dycm8009/ppt-master-studio','--harness-ref','studio-main','--harness-commit',SHA)
        st=json.loads((project/'project_state.json').read_text())
        assert st['harness']['commit']==SHA
        (project/'design_spec.md').write_text('# spec\n')
        (project/'spec_lock.md').write_text('# lock\n')
        bundle=base/'bundle.ppt-recovery.zip'
        run(ROOT/'studio/scripts/enforced_recovery.py','snapshot',project,'--output',bundle,'--label','smoke')
        with zipfile.ZipFile(bundle) as z:
            m=json.loads(z.read('PPT_MASTER_RECOVERY_MANIFEST.json'))
        assert m['schema']=='ppt-master-portable-recovery/v2'
        assert m['harness']['commit']==SHA
        restored=base/'restored'
        run(ROOT/'studio/scripts/enforced_recovery.py','restore',bundle,restored)
        rst=json.loads((restored/'project_state.json').read_text())
        assert rst['harness']['commit']==SHA
        bad='f'*40
        p=run(ROOT/'studio/scripts/enforced_preflight.py',restored,'--running-commit',bad,ok=False)
        assert p.returncode==86 and 'does not match project pin' in p.stdout
    print('studio smoke: passed')
    return 0
if __name__=='__main__': raise SystemExit(main())
