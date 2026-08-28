#!/usr/bin/env python3
from __future__ import annotations
import importlib, json, subprocess, sys, tempfile, zipfile
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
    assert v['studio_version']=='3.2.3'
    assert v['static_ui_revision']>=2
    assert v['static_ui_history_limit']==4
    assert v['project_contract_version']=='3.2.0'
    assert v['host_bootstrap_revision']>=3
    assert v['container_network_fallback_forbidden'] is True
    assert v['runtime_release_tag_pattern']=='studio-runtime-{commit}'
    assert v['runtime_release_asset_pattern']=='ppt-master-studio-runtime-{commit}.zip'
    contract=json.loads((ROOT/'studio/tests/host_bootstrap_contract.json').read_text())
    assert contract['schema']=='ppt-master-studio-host-bootstrap-contract/v3'
    assert contract['new_project_requires_recovery_bundle'] is False
    assert contract['host_capability_detection_required'] is True
    assert contract['sha_resolution_order']==['github_connector','native_web_github_api']
    assert contract['runtime_materialization_order']==['local_verified_runtime_bundle','github_connector_workflow_artifact','native_host_release_download','native_host_exact_sha_archive']
    assert contract['container_network_fallback_forbidden'] is True
    assert contract['container_network_failure_counts_as_web_attempt'] is False
    assert contract['fail_closed_only_after_supported_host_paths_exhausted'] is True
    assert contract['sha_resolution_failure_must_be_distinct_from_materialization_failure'] is True
    assert contract['ordinary_handoff_zip_is_recovery_bundle'] is False
    instructions=(ROOT/'studio/CHATGPT_PROJECT_INSTRUCTIONS.txt').read_text(encoding='utf-8')
    bootstrap=(ROOT/'studio/PROJECT_BOOTSTRAP.md').read_text(encoding='utf-8')
    host_rules=(ROOT/'studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md').read_text(encoding='utf-8')
    assert 'NEW 项目不需要 *.ppt-recovery.zip' in instructions
    assert 'Host Capability Detection' in instructions
    assert '容器网络失败只能说明容器不能联网' in instructions
    assert 'Harness materialization capability unavailable' in instructions
    assert 'A brand-new project does **not** require a Recovery Bundle.' in bootstrap
    assert 'execution container' in bootstrap and 'does not count as a public GitHub Web/API attempt' in bootstrap
    assert 'Container networking is not a Web fallback' in host_rules
    assert 'must never be reported as “public GitHub Web/API was attempted and failed.”' in host_rules
    assert 'Harness materialization capability unavailable' in host_rules
    assert (ROOT/'.github/workflows/studio-runtime-release.yml').is_file()
    static_rules=(ROOT/'studio/enforcement/PPT_MASTER_STATIC_UI_RULES.md').read_text(encoding='utf-8')
    assert 'static_ui/latest.json' in static_rules and 'unique, versioned HTML filename' in static_rules
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    adapter=importlib.import_module('studio.scripts.static_ui_adapter')
    with tempfile.TemporaryDirectory() as ui_td:
        ui_project=Path(ui_td); ui_out=ui_project/'static_ui'; ui_out.mkdir()
        (ui_out/'confirm_stage1.html').write_text('legacy',encoding='utf-8')
        counter={'n':0}
        original_render=adapter._render_surface
        try:
            def fake_render(project,surface):
                counter['n']+=1
                return f'<html><body>revision {counter["n"]}</body></html>'
            adapter._render_surface=fake_render
            names=[adapter.write_surface(ui_project,'stage1').name for _ in range(6)]
        finally:
            adapter._render_surface=original_render
        assert len(set(names))==6
        assert not (ui_out/'confirm_stage1.html').exists()
        assert len(list(ui_out.glob('confirm_stage1__*.html')))==4
        latest=json.loads((ui_out/'latest.json').read_text(encoding='utf-8'))
        assert latest['surfaces']['stage1']['file']==names[-1]
        assert (ui_out/names[-1]).is_file()
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
