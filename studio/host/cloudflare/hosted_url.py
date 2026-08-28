#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

HEX40 = re.compile(r'^[0-9a-f]{40}$')


def resolve(commit: str, config: Path | None = None) -> str:
    sha = str(commit or '').lower()
    if not HEX40.fullmatch(sha):
        raise ValueError('pinned Harness commit must be a full 40-hex SHA')
    path = config or Path(__file__).resolve().with_name('HOSTED_UI.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    pattern = str(data.get('immutable_base_pattern') or '')
    if '{commit12}' not in pattern or not pattern.startswith('https://'):
        raise ValueError('HOSTED_UI.json immutable_base_pattern is invalid')
    return pattern.replace('{commit12}', sha[:12])


def main() -> int:
    ap = argparse.ArgumentParser(description='Resolve commit-bound PPT Master Hosted UI base URL')
    ap.add_argument('commit')
    args = ap.parse_args()
    print(resolve(args.commit))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
