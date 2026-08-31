#!/usr/bin/env python3
"""
PPT Master - Preview Server Helpers

Shared network, per-project mutual-exclusion (lock), and liveness helpers for
the Flask preview servers (`svg_editor/server.py`, `confirm_ui/server.py`). Each
server keeps its own lock filename and Flask app; this module owns their
ChatGPT Work bind/browser URL split plus common process and lock behavior so
the two servers cannot drift apart.

Usage:
    from server_common import cloud_browser_url, find_free_port, validate_port

Dependencies:
    None (only uses standard library)
"""

import json
import logging
import os
import socket
import subprocess
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from workflow_transcript import DISABLE_TRANSCRIPT_ENV


MIN_PORT = 1
MAX_PORT = 65535
BIND_HOST = '0.0.0.0'
LOOPBACK_HOST = '127.0.0.1'
CLOUD_BROWSER_HOST = 'terminal.local'


def _http_url(host: str, port: int, path: str = '') -> str:
    """Return an HTTP URL for one validated preview port and optional path."""
    validated_port = validate_port(port)
    suffix = path if path.startswith('/') or not path else f'/{path}'
    return f'http://{host}:{validated_port}{suffix}'


def cloud_browser_url(port: int, path: str = '') -> str:
    """Return the ChatGPT Work Cloud Browser URL for a preview endpoint."""
    return _http_url(CLOUD_BROWSER_HOST, port, path)


def loopback_url(port: int, path: str = '') -> str:
    """Return the process-local URL used by readiness and shutdown calls."""
    return _http_url(LOOPBACK_HOST, port, path)


def validate_port(port: int) -> int:
    """Return a valid TCP port, raising ``ValueError`` outside 1..65535."""
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError('port must be an integer between 1 and 65535')
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f'port must be between {MIN_PORT} and {MAX_PORT}: {port}')
    return port


def find_free_port(preferred: int, host: str = BIND_HOST, span: int = 50) -> int:
    """Return the first bindable port from ``preferred`` through its scan span.

    The scan remains sequential so callers can keep 5050 as their preferred
    port and advance predictably when it is occupied. Invalid ports fail before
    probing, and an exhausted valid range raises ``RuntimeError`` instead of
    returning a port already known to be unavailable.
    """
    preferred = validate_port(preferred)
    if isinstance(span, bool) or not isinstance(span, int) or span <= 0:
        raise ValueError(f'span must be a positive integer: {span}')

    last_port = min(preferred + span - 1, MAX_PORT)
    for port in range(preferred, last_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f'no free TCP port on {host} in range {preferred}..{last_port}'
    )


def popen_detached(
    args: list[str],
    *,
    logger: Optional[logging.Logger] = None,
    **kwargs: object,
) -> subprocess.Popen:
    """Start a long-running child process detached from the caller.

    Windows hosts such as terminal sandboxes may place child processes in the
    caller's Job Object. ``CREATE_BREAKAWAY_FROM_JOB`` lets the local UI server
    survive after the launcher command returns; when that flag is forbidden, the
    function falls back to the previous detached-process flags.

    Detached service output remains in its component log, so the child receives
    the shared workflow-transcript opt-out environment flag.
    """
    supplied_env = kwargs.get('env')
    child_env = dict(os.environ if supplied_env is None else supplied_env)
    child_env[DISABLE_TRANSCRIPT_ENV] = '1'
    kwargs['env'] = child_env

    if os.name != 'nt':
        return subprocess.Popen(args, start_new_session=True, **kwargs)

    base_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    breakaway_flag = getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)
    try:
        return subprocess.Popen(
            args,
            creationflags=base_flags | breakaway_flag,
            **kwargs,
        )
    except OSError as exc:
        if logger is not None:
            logger.warning(
                'Windows process breakaway failed; falling back to detached '
                'process-group launch (%s)',
                exc,
            )
        return subprocess.Popen(args, creationflags=base_flags, **kwargs)


def process_alive(pid: object) -> bool:
    """Return True if a process with this pid is reachable.

    On POSIX, ``os.kill(pid, 0)`` succeeds when the process exists even without
    permission to signal it; ``PermissionError`` therefore still counts as
    alive. On Windows there is no ``os.kill(pid, 0)`` equivalent, so probe via
    ``OpenProcess`` + ``WaitForSingleObject``.
    """
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            ctypes.wintypes.DWORD,
            ctypes.wintypes.BOOL,
            ctypes.wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
        ]
        kernel32.WaitForSingleObject.restype = ctypes.wintypes.DWORD
        kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
        kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

        process_query_limited_information = 0x1000
        synchronize = 0x00100000
        wait_timeout = 0x00000102
        wait_object_0 = 0x00000000
        wait_failed = 0xFFFFFFFF

        handle = kernel32.OpenProcess(
            process_query_limited_information | synchronize,
            False,
            pid_int,
        )
        if not handle:
            return ctypes.get_last_error() == 5  # ERROR_ACCESS_DENIED
        try:
            result = kernel32.WaitForSingleObject(handle, 0)
            if result == wait_timeout:
                return True
            if result in (wait_object_0, wait_failed):
                return False
            return False
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_lock(lock_file: Path) -> Optional[dict]:
    """Read a lock file, returning the lock dict or None if absent/corrupt."""
    try:
        data = json.loads(lock_file.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def lock_pid(lock: Optional[dict]) -> int:
    """Return a valid pid from a lock dict, or 0 if absent/corrupt."""
    if not lock:
        return 0
    raw_pid = lock.get('pid', 0)
    if isinstance(raw_pid, bool):
        return 0
    if isinstance(raw_pid, int):
        return raw_pid if raw_pid > 0 else 0
    if isinstance(raw_pid, str) and raw_pid.strip().isdigit():
        return int(raw_pid.strip())
    return 0


def lock_browser_url(lock: Optional[dict]) -> Optional[str]:
    """Return a stored or port-derived Cloud Browser URL from a lock dict."""
    if not lock:
        return None
    stored_url = lock.get('browser_url')
    if isinstance(stored_url, str) and stored_url.strip():
        return stored_url.strip()
    raw_port = lock.get('port', 0)
    try:
        port = validate_port(int(raw_port))
    except (TypeError, ValueError):
        return None
    return cloud_browser_url(port)


def service_lock_reachable(
    lock: Optional[dict],
    *,
    service: str,
    project: Path,
    timeout: float = 1.0,
) -> bool:
    """Return whether a lock resolves to the expected healthy preview service.

    Host-managed command runners may place successive commands in different PID
    namespaces.  A detached child can remain reachable by port even though a
    later command cannot signal its recorded PID.  The health identity is
    therefore the cross-command authority. New locks use a random instance id;
    legacy locks fall back to matching the PID as response data rather than
    probing it from the caller's namespace.
    """
    if not lock:
        return False
    try:
        port = validate_port(int(lock.get('port', 0) or 0))
    except (TypeError, ValueError):
        return False
    pid = lock_pid(lock)
    if not pid:
        return False
    try:
        with urllib.request.urlopen(
            loopback_url(port, '/api/health'),
            timeout=timeout,
        ) as response:
            data = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return False
    if response.status != 200 or not isinstance(data, dict):
        return False
    instance_id = lock.get('instance_id')
    identity_matches = (
        data.get('instance_id') == instance_id
        if isinstance(instance_id, str) and instance_id
        else data.get('pid') == pid
    )
    return bool(
        data.get('status') == 'ok'
        and data.get('service') == service
        and data.get('project') == str(project.resolve())
        and data.get('pid') == pid
        and identity_matches
    )


def claim_lock(
    lock_file: Path,
    port: int,
    *,
    browser_url: Optional[str] = None,
) -> Optional[dict]:
    """Try to claim the per-project preview slot.

    Returns ``None`` on success. If another live process already holds the
    slot, returns the existing lock dict (caller surfaces it as an error).
    Callers must resolve and clear stale locks before claiming. New locks carry
    an unguessable instance identity so PID reuse cannot make a different
    process look like the recorded preview service.
    """
    existing = read_lock(lock_file)
    if existing and process_alive(lock_pid(existing)):
        return existing
    payload = {
        'pid': os.getpid(),
        'port': port,
        'instance_id': uuid.uuid4().hex,
    }
    if browser_url:
        payload['browser_url'] = browser_url
    lock_file.write_text(json.dumps(payload), encoding='utf-8')
    return None


def release_lock(lock_file: Path) -> None:
    """Best-effort cleanup: only delete the lock if it still names *us*."""
    try:
        current = read_lock(lock_file)
        if lock_pid(current) == os.getpid():
            lock_file.unlink(missing_ok=True)
    except OSError:
        pass


def clear_lock(lock_file: Path) -> None:
    """Best-effort cleanup for a lock already proven stale by the caller."""
    try:
        lock_file.unlink(missing_ok=True)
    except OSError:
        pass
