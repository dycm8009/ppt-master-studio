#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
SHA = subprocess.run(
    ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip().lower()

DELETED_CONTROL_DOCS = [
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

RUNTIME_HOST_FILES = [
    'studio/host/cloudflare/HOSTED_UI.json',
    'studio/host/cloudflare/hosted_url.py',
    'studio/host/cloudflare/hosted_confirm_handoff.py',
    'studio/host/cloudflare/hosted_confirm_bridge.py',
    'studio/host/cloudflare/hosted_editor_bridge.py',
]


def run(*args, ok=True):
    proc = subprocess.run(
        [PY, *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if ok and proc.returncode != 0:
        raise AssertionError(
            f'command failed: {args}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}'
        )
    return proc


def main() -> int:
    version = json.loads((ROOT / 'studio/VERSION.json').read_text(encoding='utf-8'))
    assert version['studio_version'] == '3.4.1'
    assert version['project_contract_version'] == '3.2.0'
    assert version['host_bootstrap_revision'] >= 8
    assert version['control_plane_revision'] >= 5
    assert version['hosted_ui_revision'] >= 1
    assert version['official_confirm_host_revision'] >= 1
    assert version['official_svg_editor_host_revision'] >= 1
    assert version['motion_review_surface'] is False
    assert 'Cloudflare' in version['hosted_ui_policy']
    assert 'official Confirm UI frontend' in version['hosted_confirm_policy']
    assert 'pinned local official Confirm UI server' in version['hosted_confirm_policy']
    assert 'official SVG Editor frontend' in version['hosted_editor_policy']
    assert 'filesystem mutation authority' in version['hosted_editor_policy']
    assert 'immutable Cloudflare Worker' in version['hosted_ui_immutable_worker_policy']
    assert 'branch and artifact actions' in version['fresh_chat_bootstrap_policy']
    assert 'matching non-expired Runtime artifact' in version['fresh_chat_bootstrap_policy']
    assert 'frozen' in version['mini_app_transport_policy']
    assert 'not part of the default v3.4.x Runtime bundle' in version['stage1_mini_app_policy']
    assert 'never decision ownership' in version['human_confirmation_fallback_policy']
    assert version['connector_discovery_required'] is True
    assert version['preloaded_tool_absence_is_connector_unavailable'] is False
    assert version['fresh_sha_resolution_required'] is True
    assert version['host_download_primitive_allowed'] is True
    assert version['container_network_fallback_forbidden'] is True

    instructions = (ROOT / 'studio/CHATGPT_PROJECT_INSTRUCTIONS.txt').read_text(encoding='utf-8')
    entry = (ROOT / 'studio/host/chatgpt/ENTRYPOINT.md').read_text(encoding='utf-8')
    host_rules = (ROOT / 'studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md').read_text(encoding='utf-8')
    host_contract = json.loads((ROOT / 'studio/tests/host_bootstrap_contract.json').read_text(encoding='utf-8'))
    assert len(instructions.encode('utf-8')) < 1400
    assert '不得直接进入普通 slides authoring' in instructions
    assert 'studio/host/chatgpt/ENTRYPOINT.md' in instructions
    assert '只按当前步骤需要加载文件' in instructions
    assert 'Workflow、Gate、Template、Image、Motion、Recovery 与 QA' in instructions
    assert 'Stage 1' not in instructions
    assert 'Cloudflare' not in instructions

    for required in [
        'Cloudflare-hosted official Confirm UI',
        'hosted_url.py',
        'hosted_confirm_bridge.py',
        'hosted_confirm_handoff.py',
        'captured-not-validated',
        'Cloudflare-hosted official SVG Editor',
        'hosted_editor_bridge.py',
        'captured-not-applied',
        'no separate Studio Motion Review page',
        'Frozen legacy transports',
        'Human-confirmation invariant',
        'current-session `studio-main` **branch metadata**',
        'workflow/artifact actions',
        'artifact-download action',
    ]:
        assert required in entry, required
    assert 'immutable Worker URL' in entry
    assert 'never silently use a newer `latest` Hosted UI for a RESUME project' in entry
    assert 'Do not ask the user to copy a token, long JSON URL, or confirmation JSON' in entry
    assert 'execution-container networking' in entry
    assert 'dynamic connector discovery' in entry
    assert 'Do not report `artifact_download: unavailable/not exposed`' in entry
    assert 'change only the transport, never the owner of the decision' in entry
    assert 'wait for an explicit user confirmation or revision' in entry

    assert 'Deterministic ChatGPT connector discovery' in host_rules
    assert 'Absence from the initially preloaded tool list is not proof' in host_rules
    assert '`head_sha` exactly equals the pinned SHA' in host_rules
    assert '`artifact_download: not exposed` is not a valid failure reason' in host_rules
    assert 'Harness materialization capability unavailable' in host_rules
    assert 'does not define PPT workflow' in host_rules

    assert host_contract['schema'] == 'ppt-master-studio-host-bootstrap-contract/v6'
    assert host_contract['connector_resource_discovery_required'] is True
    assert host_contract['connector_branch_metadata_authoritative_when_available'] is True
    assert host_contract['code_search_commit_page_or_cached_web_cannot_define_current_head'] is True
    assert host_contract['artifact_actions_must_be_discovered_before_failure'] is True
    assert host_contract['matching_nonexpired_artifact_must_be_download_attempted'] is True
    assert host_contract['runtime_artifact_workflow_head_sha_must_equal_pin'] is True

    hosted = json.loads((ROOT / 'studio/host/cloudflare/HOSTED_UI.json').read_text(encoding='utf-8'))
    assert hosted['schema'] == 'ppt-master-studio-hosted-ui-config/v2'
    assert hosted['provider'] == 'cloudflare-workers'
    assert hosted['immutable_base_pattern'] == 'https://ppt-master-hosted-{commit12}.dycm-lab.workers.dev'
    assert hosted['immutable_worker_name_pattern'] == 'ppt-master-hosted-{commit12}'
    assert hosted['authority']['confirm'] == 'local-pinned-official-confirm-ui'
    assert hosted['authority']['svg_editor'] == 'local-pinned-official-svg-editor'
    assert hosted['motion_review_surface'] is False
    assert 'pinned 40-hex Harness commit' in hosted['pinned_asset_policy']

    # Every stable commit is a possible NEW-project pin, so every push to studio-main
    # must deploy its own immutable Hosted UI Worker even when UI source files did not change.
    deploy = (ROOT / '.github/workflows/hosted-official-ui-deploy-prod.yml').read_text(encoding='utf-8')
    deploy_trigger = deploy.split('\njobs:', 1)[0]
    assert 'branches: [studio-main]' in deploy_trigger
    assert '\n    paths:' not in deploy_trigger

    # The resolver must bind the browser surface to the exact project pin.
    resolved = run(ROOT / 'studio/host/cloudflare/hosted_url.py', SHA).stdout.strip()
    assert resolved == f'https://ppt-master-hosted-{SHA[:12]}.dycm-lab.workers.dev'
    bad = run(ROOT / 'studio/host/cloudflare/hosted_url.py', 'bad-sha', ok=False)
    assert bad.returncode != 0

    # Runtime bridges must compile without loading any legacy mini/static UI path.
    for rel in RUNTIME_HOST_FILES[1:]:
        run('-m', 'py_compile', ROOT / rel)
    assert (ROOT / 'studio/host/cloudflare/hosted_confirm_handoff.py').is_file()
    assert (ROOT / 'studio/host/cloudflare/hosted_confirm_bridge.py').is_file()
    assert (ROOT / 'studio/host/cloudflare/hosted_editor_bridge.py').is_file()

    # Official Harness owns Stage-1 confirmation semantics.
    confirm_ui = (ROOT / 'skills/ppt-master/scripts/docs/confirm_ui.md').read_text(encoding='utf-8')
    assert 'The handoff is context, not confirmation, and silence confirms' in confirm_ui
    assert 'open chat questions and wait explicitly' in confirm_ui
    assert 'recommendations.stage1.json' in confirm_ui
    assert 'template_options.json' in confirm_ui
    assert 'without fabricating these UI receipts' in confirm_ui

    for rel in DELETED_CONTROL_DOCS:
        assert not (ROOT / rel).exists(), f'duplicate control document still present: {rel}'

    # Runtime Release must be minimal and must not ship frozen experimental UI code.
    release = (ROOT / '.github/workflows/studio-runtime-release.yml').read_text(encoding='utf-8')
    assert 'zip -qr "$ASSET" .' not in release
    assert 'skills/ppt-master' in release
    assert 'studio/host/chatgpt/ENTRYPOINT.md' in release
    assert 'PPT_MASTER_HOST_CAPABILITY_RULES.md' in release
    for rel in RUNTIME_HOST_FILES:
        assert rel in release, rel
    for forbidden in [
        'studio/scripts/mini_app_builder.py',
        'studio/scripts/stage1_mini_app.py',
        'studio/scripts/static_ui_adapter.py',
        'studio/static_ui',
        'studio/artifact_ui_poc',
        'studio/regression',
        'studio/host/cloudflare/worker.js',
        'studio/host/cloudflare/worker_production.js',
        'studio/host/cloudflare/test_',
    ]:
        assert forbidden not in release, forbidden

    run(
        ROOT / 'studio/scripts/enforced_bootstrap.py',
        '--repo-root', ROOT,
        '--running-commit', SHA,
    )

    # Portable recovery still pins and rejects a mismatched Harness commit.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        project = base / 'project'
        run(
            ROOT / 'studio/scripts/enforced_checkpoint.py',
            project,
            '--phase', 'intake',
            '--harness-repo', 'dycm8009/ppt-master-studio',
            '--harness-ref', 'studio-main',
            '--harness-commit', SHA,
        )
        state = json.loads((project / 'project_state.json').read_text(encoding='utf-8'))
        assert state['harness']['commit'] == SHA
        (project / 'design_spec.md').write_text('# spec\n', encoding='utf-8')
        (project / 'spec_lock.md').write_text('# lock\n', encoding='utf-8')
        bundle = base / 'bundle.ppt-recovery.zip'
        run(
            ROOT / 'studio/scripts/enforced_recovery.py',
            'snapshot', project,
            '--output', bundle,
            '--label', 'smoke',
        )
        with zipfile.ZipFile(bundle) as zf:
            manifest = json.loads(zf.read('PPT_MASTER_RECOVERY_MANIFEST.json'))
        assert manifest['schema'] == 'ppt-master-portable-recovery/v2'
        assert manifest['harness']['commit'] == SHA
        restored = base / 'restored'
        run(ROOT / 'studio/scripts/enforced_recovery.py', 'restore', bundle, restored)
        mismatch = run(
            ROOT / 'studio/scripts/enforced_preflight.py',
            restored,
            '--running-commit', 'f' * 40,
            ok=False,
        )
        assert mismatch.returncode == 86
        assert 'does not match project pin' in mismatch.stdout

    print('studio v3.4.1 fresh-chat bootstrap + Hosted official UI smoke: passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
