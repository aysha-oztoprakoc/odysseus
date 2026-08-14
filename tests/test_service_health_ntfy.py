"""Tests for src.service_health — ntfy."""
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

def test_ntfy_disabled_without_integration():
    s = sh.ntfy_health([], {'reminder_channel': 'ntfy'})
    assert s['status'] == sh.DISABLED

def test_ntfy_ok():
    s = sh.ntfy_health(_ntfy_intg(), {'reminder_channel': 'ntfy'}, http_get=lambda url, timeout: _resp(200))
    assert s['status'] == sh.OK
    assert s['meta']['base'] == 'http://ntfy:80'

def test_ntfy_probes_v1_health_not_a_topic():
    seen = {}

    def getter(url, timeout):
        seen['url'] = url
        return _resp(200)
    sh.ntfy_health(_ntfy_intg(), {'reminder_channel': 'ntfy'}, http_get=getter)
    assert seen['url'].endswith('/v1/health')

def test_ntfy_down_on_exception():
    s = sh.ntfy_health(_ntfy_intg(), {'reminder_channel': 'ntfy'}, http_get=_raise)
    assert s['status'] == sh.DOWN

def test_ntfy_meta_redacts_userinfo_in_base():
    intg = [{'preset': 'ntfy', 'enabled': True, 'base_url': 'https://user:topsecret@ntfy.example.com'}]
    seen = {}

    def getter(url, timeout):
        seen['url'] = url
        return _resp(200)
    s = sh.ntfy_health(intg, {'reminder_channel': 'ntfy'}, http_get=getter)
    assert s['meta']['base'] == 'https://ntfy.example.com'
    assert 'topsecret' not in repr(s)