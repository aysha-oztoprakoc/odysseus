"""Regression tests: AUTH_ENABLED=false must fail closed for remote callers.

Audit residual: `require_admin` honored AUTH_ENABLED=false for ANY caller,
so a public deployment with auth accidentally disabled would answer every
request. The bypass is now loopback-only; remote callers get 403.

Pattern: call `require_admin` directly with fake Request objects (same
pattern as tests/test_auth_regressions.py) so coverage lands on the real
closure without spinning up middleware.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from core.middleware import require_admin


def _req(host="127.0.0.1", user=None):
    state = SimpleNamespace(current_user=user)
    return SimpleNamespace(state=state, client=SimpleNamespace(host=host), headers={})


def _auth_manager(configured=True):
    mgr = MagicMock()
    mgr.is_configured = configured
    mgr.is_admin.return_value = True
    return mgr


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    monkeypatch.delenv("ODYSSEUS_INTERNAL_TOKEN", raising=False)
    yield


def test_auth_disabled_allows_loopback(monkeypatch):
    """AUTH_ENABLED=false + loopback caller -> allowed (single-user mode)."""
    monkeypatch.setenv("AUTH_ENABLED", "false")
    req = _req(host="127.0.0.1")
    app_state = SimpleNamespace(auth_manager=_auth_manager())
    req.app = SimpleNamespace(state=app_state)

    require_admin(req)  # must not raise


def test_auth_disabled_rejects_remote(monkeypatch):
    """AUTH_ENABLED=false + remote caller -> 403 (fail closed when exposed)."""
    monkeypatch.setenv("AUTH_ENABLED", "false")
    req = _req(host="203.0.113.10")
    app_state = SimpleNamespace(auth_manager=_auth_manager())
    req.app = SimpleNamespace(state=app_state)

    with pytest.raises(HTTPException) as exc:
        require_admin(req)
    assert exc.value.status_code == 403


def test_auth_disabled_rejects_remote_even_with_configured_admin(monkeypatch):
    """Configured admin manager does not re-open remote when auth is disabled."""
    monkeypatch.setenv("AUTH_ENABLED", "false")
    req = _req(host="198.51.100.7")
    app_state = SimpleNamespace(auth_manager=_auth_manager(configured=True))
    req.app = SimpleNamespace(state=app_state)

    with pytest.raises(HTTPException) as exc:
        require_admin(req)
    assert exc.value.status_code == 403
