"""Tests for src.service_health — chromadb."""
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

def test_chromadb_both_healthy_ok():
    s = sh.chromadb_health(_Store(True), _Store(True))
    assert s['status'] == sh.OK
    assert s['meta'] == {'rag': True, 'memory': True}

def test_chromadb_one_down_degraded():
    s = sh.chromadb_health(_Store(True), _Store(False))
    assert s['status'] == sh.DEGRADED

def test_chromadb_both_unhealthy_down():
    s = sh.chromadb_health(_Store(False), _Store(False))
    assert s['status'] == sh.DOWN

def test_chromadb_both_absent_disabled():
    s = sh.chromadb_health(None, None)
    assert s['status'] == sh.DISABLED

def test_chromadb_one_absent_one_healthy_ok():
    s = sh.chromadb_health(_Store(True), None)
    assert s['status'] == sh.OK
    assert s['meta']['memory'] is None