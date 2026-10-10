"""Explicit Codex status reports; no private database inspection."""
import time

_report = None
LABELS = {'busy': '工作中', 'idle': '空闲', 'wait': '等待中', 'off': '离线'}


def report_status(kind, session_id, ttl=300):
    global _report
    if kind not in LABELS:
        raise ValueError('invalid status')
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError('session_id is required')
    ttl = int(ttl)
    if not 10 <= ttl <= 3600:
        raise ValueError('ttl must be between 10 and 3600 seconds')
    _report = {'source': 'codex', 'kind': kind, 'session_id': session_id,
               'expires': time.monotonic() + ttl}
    return snapshot()


def snapshot():
    if _report is None:
        return None
    return {'source': 'codex', 'session_id': _report['session_id'],
            'kind': _report['kind'] if time.monotonic() < _report['expires'] else 'off',
            'expired': time.monotonic() >= _report['expires']}


def read_status():
    value = snapshot()
    return (value['kind'], LABELS[value['kind']]) if value else None
