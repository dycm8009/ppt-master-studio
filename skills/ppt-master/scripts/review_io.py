#!/usr/bin/env python3
"""PPT Master - Derived review file publication.

Usage: imported by review handoff scripts.
Examples: write_text_atomic(Path('live_preview/storyboard.html'), html)
Dependencies: standard library only.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile


def write_text_atomic(path: Path, content: str) -> None:
    """Replace a single derived file without exposing a partial write."""
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
