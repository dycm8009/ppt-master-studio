#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hosted_confirm_handoff as handoff  # noqa: E402


def decode(url: str, prefix: str) -> dict:
    encoded = url.split(prefix, 1)[1]
    raw = base64.urlsafe_b64decode(encoded + '=' * ((4 - len(encoded) % 4) % 4))
    return json.loads(gzip.decompress(raw).decode('utf-8'))


def main() -> int:
    # Deliberately verbose Stage-2-like data: the old uncompressed browser
    # transport made this kind of payload visibly huge and could be truncated.
    candidates = []
    for i in range(3):
        candidates.append({
            'id': f'direction-{i}',
            'name_zh': f'设计方向 {i}',
            'note_zh': '强调系统边界、证据链、工程执行与性能诊断。' * 28,
            'mode': 'custom',
            'visual_style': 'dark-tech',
            'color': {'palette': {
                'background': '#0B0D12', 'secondary_bg': '#171B24',
                'primary': '#F4F7FB', 'accent': '#E66C63',
                'secondary_accent': '#53A7FF', 'body_text': '#C9D2DF',
            }},
            'typography': {'heading': {'primary': 'DengXian'}, 'body': {'primary': 'Microsoft YaHei'}},
            'image_strategy': {'behavior': '只生成具有明确解释目的的结构化技术图。' * 24},
        })
    snapshot = {
        'session': {'phase': 'strategist', 'status': 'active', 'current_stage': 'stage2', 'recommendation_stage_number': 2},
        'recommendations': {
            'stage': 'stage2', 'lang': 'zh',
            'page_count': {'value': '16-20'},
            'design_directions': {'selected': 1, 'candidates': candidates},
            'image_notes': {'value': '架构页优先系统图与调用链，性能页优先 Trace 证据。' * 30},
        },
    }
    base = 'https://ppt-master-hosted.example'
    session = '1' * 48
    host_key = '2' * 64
    commit = '3' * 40
    boot = handoff.build_bootstrap_url(base, commit, snapshot, session=session, host_key=host_key)
    assert len(boot['url']) < handoff.MAX_URL_CHARS
    assert handoff.BOOTSTRAP_PREFIX in boot['url']
    boot_value = decode(boot['url'], handoff.BOOTSTRAP_PREFIX)
    assert boot_value['schema'] == 'ppt-master-hosted-official-bootstrap-handoff/v3'
    assert boot_value['payload']['api_snapshot'] == snapshot
    advance = handoff.build_advance_url(base, session, host_key, snapshot)
    assert len(advance['url']) < handoff.MAX_URL_CHARS
    assert handoff.ADVANCE_PREFIX in advance['url']
    advance_value = decode(advance['url'], handoff.ADVANCE_PREFIX)
    assert advance_value['schema'] == 'ppt-master-hosted-official-advance-handoff/v2'
    assert advance_value['api_snapshot'] == snapshot
    print(f"compact Confirm UI handoff: passed (bootstrap={len(boot['url'])}, advance={len(advance['url'])} chars)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
