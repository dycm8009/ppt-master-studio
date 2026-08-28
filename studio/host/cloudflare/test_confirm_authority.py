#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hosted_confirm_handoff as bridge  # noqa: E402


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> int:
    commit = '7' * 40
    session = '8' * 48
    host_key = '9' * 64
    with tempfile.TemporaryDirectory(prefix='ppt-master-confirm-authority-') as td:
        project = Path(td) / 'project'
        confirm = project / 'confirm_ui'
        confirm.mkdir(parents=True)
        write_json(confirm / 'template_options.json', {
            'schema_version': 1, 'phase': 'template', 'default_mode': 'free_design',
            'lang': 'zh', 'explicit_workspace_roots': [],
        })
        write_json(confirm / 'recommendations.stage1.json', {
            'stage': 'stage1', 'lang': 'zh', 'primary_language': 'zh-CN',
            'recommend': {'canvas': 'ppt169'},
            'audience': {'value': 'C++ 开发工程师'},
            'communication_intent': {'value': '解释 AI 友好型架构并形成工程决策'},
            'audience_outcome': {'value': '理解关键系统边界'},
            'core_message': {'value': '可验证、可观测、可执行'},
            'delivery_context': {'value': '技术分享'},
            'artifact_afterlife': {'value': '设计评审参考'},
            'content_divergence': {'value': ''},
        })
        generated = bridge.build_bootstrap_url(
            'https://ppt-master-hosted.example', commit,
            {'session': {}, 'recommendations': {'stage': 'stage1'}},
            session=session, host_key=host_key,
        )
        bridge._persist_bootstrap_state(project, 'https://ppt-master-hosted.example', commit, generated)
        payload = {
            'stage': 'stage1', 'primary_language': 'zh-CN', 'canvas': 'ppt169',
            'audience': 'C++ 开发工程师',
            'communication_intent': '解释 AI 友好型架构并形成工程决策',
            'audience_outcome': '理解关键系统边界',
            'core_message': '可验证、可观测、可执行',
            'delivery_context': '技术分享',
            'artifact_afterlife': '设计评审参考', 'content_divergence': '',
            'template_selection': {'mode': 'free_design', 'selection_keys': []},
        }
        response = {
            'schema': 'ppt-master-hosted-official-captured/v1',
            'status': 'captured-not-validated', 'harness_status': 'not-validated',
            'harness_commit': commit, 'active_stage': 'stage1',
            'captures': [{'stage': 'stage1', 'payload': payload, 'captured_at': '2026-08-28T00:00:00Z'}],
            'session_status': 'waiting-agent',
        }
        applied = bridge.apply_response(project, response, 'stage1')
        assert applied['status'] == 'validated-and-persisted-by-pinned-harness'
        result = json.loads((confirm / 'result.json').read_text(encoding='utf-8'))
        selection = json.loads((confirm / 'template_selection.json').read_text(encoding='utf-8'))
        assert result['stage'] == 'stage1' and result['status'] == 'stage1-confirmed'
        assert result['canvas'] == 'ppt169'
        assert selection['status'] == 'confirmed' and selection['mode'] == 'free_design'
        assert selection['selections'] == []
    print('hosted Confirm capture -> pinned official receipt authority: passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
