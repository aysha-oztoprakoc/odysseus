"""Tests for src.service_health — core."""
import types
import pytest
from src import service_health as sh

def _resp(status_code):
    return types.SimpleNamespace(status_code=status_code)

def _raise(*_a, **_k):
    raise RuntimeError('connection refused')

class _Store:

    def __init__(self, healthy):
        self.healthy = healthy

def _ntfy_intg():
    return [{'preset': 'ntfy', 'enabled': True, 'base_url': 'http://ntfy:80'}]

def _acct(name, host='imap.example.com'):
    return {'account_id': name, 'account_name': name, 'imap_host': host, 'imap_password': 'hunter2'}

class _Conn:

    def logout(self):
        pass

def _ep(name):
    return {'name': name, 'base_url': f'http://{name}:8000/v1', 'api_key': 'sk-secret'}

def test_rollup_picks_worst_non_disabled():
    services = [{'status': sh.OK}, {'status': sh.DISABLED}, {'status': sh.DEGRADED}, {'status': sh.OK}]
    assert sh._rollup(services) == sh.DEGRADED

def test_rollup_down_beats_degraded():
    assert sh._rollup([{'status': sh.DEGRADED}, {'status': sh.DOWN}]) == sh.DOWN

def test_rollup_all_disabled_is_ok():
    assert sh._rollup([{'status': sh.DISABLED}, {'status': sh.DISABLED}]) == sh.OK

def test_collect_service_health_shape(monkeypatch):
    import asyncio
    monkeypatch.setattr(sh, '_gather_inputs', lambda: {'settings': {'search_provider': 'disabled'}, 'integrations': [], 'accounts': [], 'endpoints': []})
    out = asyncio.run(sh.collect_service_health(_Store(True), _Store(True)))
    assert set(out) == {'overall', 'services', 'timestamp'}
    names = {s['name'] for s in out['services']}
    assert names == {'chromadb', 'searxng', 'ntfy', 'email', 'providers'}
    assert out['overall'] == sh.OK

@pytest.mark.parametrize('raw,expected', [('http://user:pass@host:8080/path?api_key=secret#frag', 'http://host:8080/path'), ('https://admin:hunter2@searx.example.com/', 'https://searx.example.com'), ('http://ntfy.local:80?token=abc', 'http://ntfy.local:80'), ('host:8080', 'host:8080'), ('', ''), (None, '')])
def test_safe_url_strips_secrets(raw, expected):
    out = sh._safe_url(raw)
    assert out == expected
    for bad in ('pass', 'secret', 'hunter2', 'abc', 'token', '@'):
        if raw and bad in raw and (bad not in expected):
            assert bad not in out

def test_classify_error_categories():
    import socket
    assert sh._classify_error(TimeoutError()) == 'timeout'
    assert sh._classify_error(socket.timeout()) == 'timeout'
    assert sh._classify_error(socket.gaierror()) == 'dns_error'
    assert sh._classify_error(ConnectionRefusedError()) == 'connection_refused'
    assert sh._classify_error(OSError('boom')) == 'network_error'
    assert sh._classify_error(ValueError('x')) == 'error'

def test_collect_runs_subsystems_concurrently(monkeypatch):
    import asyncio
    import time
    monkeypatch.setattr(sh, '_gather_inputs', lambda: {'settings': {}, 'integrations': [], 'accounts': [], 'endpoints': []})

    def slow(name):

        def _fn(*_a, **_k):
            import threading
            threading.Event().wait(0.6)
            return {'name': name, 'status': sh.OK, 'detail': '', 'meta': {}}
        return _fn
    monkeypatch.setattr(sh, 'searxng_health', slow('searxng'))
    monkeypatch.setattr(sh, 'ntfy_health', slow('ntfy'))
    monkeypatch.setattr(sh, 'email_health', slow('email'))
    monkeypatch.setattr(sh, 'providers_health', slow('providers'))
    t0 = time.monotonic()
    out = asyncio.run(sh.collect_service_health(None, None))
    elapsed = time.monotonic() - t0
    assert elapsed < 1.5, f'subsystems not concurrent: took {elapsed:.1f}s'
    assert {s['name'] for s in out['services']} == {'chromadb', 'searxng', 'ntfy', 'email', 'providers'}

def test_collect_aggregate_deadline_yields_controlled_result(monkeypatch):
    import asyncio
    import time
    monkeypatch.setattr(sh, '_AGGREGATE_DEADLINE', 0.5)
    monkeypatch.setattr(sh, '_SUBSYSTEM_DEADLINE', 0.4)
    monkeypatch.setattr(sh, '_gather_inputs', lambda: {'settings': {}, 'integrations': [], 'accounts': [], 'endpoints': []})

    async def _slow_gather(*coros, **_k):
        for c in coros:
            close = getattr(c, 'close', None)
            if close:
                close()
        await asyncio.sleep(5)
    monkeypatch.setattr(sh.asyncio, 'gather', _slow_gather)
    t0 = time.monotonic()
    out = asyncio.run(sh.collect_service_health(None, None))
    elapsed = time.monotonic() - t0
    assert elapsed < 2, f'aggregate deadline did not bound: {elapsed:.1f}s'
    assert set(out) == {'overall', 'services', 'timestamp'}
    net = [s for s in out['services'] if s['name'] != 'chromadb']
    assert all((s['status'] == sh.DOWN and s['meta'].get('error') == 'timeout' for s in net))