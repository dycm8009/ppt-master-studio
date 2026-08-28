#!/usr/bin/env python3
from __future__ import annotations
import importlib, json, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PY=sys.executable
SHA=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip().lower()

DELETED_CONTROL_DOCS=[
    'studio/PROJECT_BOOTSTRAP.md',
    'studio/PROJECT_ROUTER_MIGRATION.md',
    'studio/HOST_BOOTSTRAP_CHANGELOG.md',
    'studio/enforcement/PPT_MASTER_AUTHORITY.md',
    'studio/enforcement/PPT_MASTER_WORKFLOW.md',
    'studio/enforcement/PPT_MASTER_TEMPLATE_RULES.md',
    'studio/enforcement/PPT_MASTER_REGRESSION_POLICY.md',
    'studio/enforcement/PPT_MASTER_STATIC_UI_RULES.md',
    'studio/enforcement/PPT_MASTER_RECOVERY_RULES.md',
]

def run(*args, ok=True):
    p=subprocess.run([PY,*map(str,args)],cwd=ROOT,text=True,capture_output=True)
    if ok and p.returncode!=0:
        raise AssertionError(f'command failed: {args}\nSTDOUT={p.stdout}\nSTDERR={p.stderr}')
    return p

def main():
    v=json.loads((ROOT/'studio/VERSION.json').read_text())
    assert v['studio_version']=='3.3.1'
    assert v['project_contract_version']=='3.2.0'
    assert v['host_bootstrap_revision']>=6
    assert v['project_router_revision']>=2
    assert v['control_plane_revision']>=2
    assert 'host adapter only' in v['control_plane_policy']
    assert 'minimal PPT-to-Studio routing contract' in v['project_router_policy']
    assert 'Load only' in v['lazy_load_policy']
    assert 'whitelist' in v['runtime_bundle_policy']
    assert 'never decision ownership' in v['human_confirmation_fallback_policy']
    assert 'wait for explicit user confirmation or revision' in v['human_confirmation_fallback_policy']
    assert v['connector_discovery_required'] is True
    assert v['preloaded_tool_absence_is_connector_unavailable'] is False
    assert v['fresh_sha_resolution_required'] is True
    assert v['host_download_primitive_allowed'] is True
    assert v['container_network_fallback_forbidden'] is True

    contract=json.loads((ROOT/'studio/tests/host_bootstrap_contract.json').read_text())
    assert contract['schema']=='ppt-master-studio-host-bootstrap-contract/v5'
    assert contract['new_project_requires_recovery_bundle'] is False
    assert contract['connector_resource_discovery_required'] is True
    assert contract['preloaded_tool_absence_counts_as_connector_unavailable'] is False
    assert contract['fresh_sha_must_come_from_current_session_branch_metadata'] is True
    assert contract['container_network_fallback_forbidden'] is True
    assert contract['project_instructions_are_minimal_router_only'] is True
    assert contract['official_harness_owns_ppt_workflow'] is True
    assert contract['lazy_supporting_document_loading_required'] is True
    assert contract['duplicate_studio_authority_documents_allowed'] is False
    assert contract['runtime_bundle_is_whitelist'] is True
    assert contract['confirmation_surface_failure_changes_transport_only'] is True
    assert contract['chat_fallback_requires_explicit_user_confirmation_unless_delegated'] is True
    assert contract['fallback_notice_counts_as_confirmation'] is False
    assert contract['assistant_recommendation_counts_as_confirmation'] is False
    assert contract['silence_counts_as_confirmation'] is False

    instructions=(ROOT/'studio/CHATGPT_PROJECT_INSTRUCTIONS.txt').read_text(encoding='utf-8')
    entry=(ROOT/'studio/host/chatgpt/ENTRYPOINT.md').read_text(encoding='utf-8')
    host_rules=(ROOT/'studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md').read_text(encoding='utf-8')
    assert len(instructions.encode('utf-8')) < 1400
    assert '不得直接进入普通 slides authoring' in instructions
    assert 'studio/host/chatgpt/ENTRYPOINT.md' in instructions
    assert '只按当前步骤需要加载文件' in instructions
    assert 'Workflow、Gate、Template、Image、Motion、Recovery 与 QA' in instructions
    assert 'Stage 1' not in instructions
    assert 'app_block' not in instructions
    assert 'studio-runtime-' not in instructions
    assert 'RESUME' in entry and 'NEW' in entry
    assert 'skills/ppt-master/SKILL.md' in entry
    assert 'skills/ppt-master/workflows/routing.md' in entry
    assert 'Load only that route' in entry
    assert 'Do not preload Studio workflow/template/UI/motion/QA policy' in entry
    assert 'discover connector resources' in entry
    assert 'execution-container networking' in entry
    assert 'Human-confirmation invariant' in entry
    assert 'change only the transport, never the owner of the decision' in entry
    assert 'wait for an explicit user confirmation or revision' in entry
    assert 'fallback notice' in entry and 'is not user confirmation' in entry
    assert 'Absence from the initially preloaded tool list is not proof' in host_rules
    assert 'Harness materialization capability unavailable' in host_rules
    assert 'does not define PPT workflow' in host_rules
    assert len(host_rules.encode('utf-8')) < 5000

    # Upstream already owns the same semantic boundary: after page failure/timeout,
    # chat must ask the unresolved Stage-1 items and wait explicitly.
    confirm_ui=(ROOT/'skills/ppt-master/scripts/docs/confirm_ui.md').read_text(encoding='utf-8')
    assert 'The handoff is context, not confirmation, and silence confirms' in confirm_ui
    assert 'present the same combined Stage-1 items as open chat questions and wait explicitly' in confirm_ui

    for rel in DELETED_CONTROL_DOCS:
        assert not (ROOT/rel).exists(), f'duplicate control document still present: {rel}'

    release=(ROOT/'.github/workflows/studio-runtime-release.yml').read_text(encoding='utf-8')
    assert 'zip -qr "$ASSET" .' not in release
    assert 'skills/ppt-master' in release
    assert 'studio/host/chatgpt/ENTRYPOINT.md' in release
    assert 'PPT_MASTER_HOST_CAPABILITY_RULES.md' in release
    assert 'studio/artifact_ui_poc' not in release
    assert 'studio/regression' not in release

    run(ROOT/'studio/scripts/enforced_bootstrap.py','--repo-root',ROOT,'--running-commit',SHA)

    # Static UI remains a host fallback component, but it is not bootstrap authority.
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    adapter=importlib.import_module('studio.scripts.static_ui_adapter')
    with tempfile.TemporaryDirectory() as ui_td:
        ui_project=Path(ui_td); ui_out=ui_project/'static_ui'; ui_out.mkdir()
        (ui_out/'confirm_stage1.html').write_text('legacy',encoding='utf-8')
        counter={'n':0}; original_render=adapter._render_surface
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

    # Portable recovery remains only for host filesystem-loss continuation.
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
        bad='f'*40
        p=run(ROOT/'studio/scripts/enforced_preflight.py',restored,'--running-commit',bad,ok=False)
        assert p.returncode==86 and 'does not match project pin' in p.stdout

    print('studio v3.3.1 control-plane smoke: passed')
    return 0
if __name__=='__main__': raise SystemExit(main())
