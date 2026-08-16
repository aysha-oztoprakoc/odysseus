"""Regression tests: unconfigured auth must NOT imply admin on a network-exposed server.

Audit residual (Phase 4(i)): `routes.task_routes._is_admin` returned True for
ANY user when ``AuthManager.is_configured`` was False — regardless of whether
the server was bound off-loopback. On a public instance with no admin account,
that would let any caller issue shell-executing task actions (`run_local`,
`run_script`, `ssh_command`) before setup ever happened.

Fix: the implicit-owner trust is gated on ``core.middleware.is_loopback_bound()``,
mirroring how ``require_admin`` already fails closed for remote callers when
``AUTH_ENABLED=false``. This regression pins the new helper and confirms the
task-router closure consults it in the unconfigured branch.

``_is_admin`` is a closure inside ``setup_task_routes``, so it can't be imported
directly; we assert the wiring (source-level) plus the helper's behavior
(behaviour-level) so a future regression that removes the loopback guard is
caught without needing the full FastAPI app.
"""

import pytest

from core.middleware import is_loopback_bound
from pathlib import Path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("APP_BIND", raising=False)
    yield


# ── is_loopback_bound: the trust gate ──────────────────────────────────────
# APP_BIND defaults to 127.0.0.1 (loopback-safe). Explicit loopback values
# must keep the single-operator trust; any network-exposed binding must fail
# closed (return False).

def test_loopback_bound_when_unset_defaults_to_loopback():
    assert is_loopback_bound() is True


@pytest.mark.parametrize("bind", [
    "127.0.0.1",
    "::1",
    "localhost",
    "127.0.0.1 ::1 localhost",   # multi-address, all loopback
    "127.0.0.1,::1",             # comma-separated, all loopback
])
def test_loopback_bound_accepts_loopback_only(monkeypatch, bind):
    monkeypatch.setenv("APP_BIND", bind)
    assert is_loopback_bound() is True


@pytest.mark.parametrize("bind", [
    "0.0.0.0",
    "::",
    "192.168.1.10",
    "10.0.0.5",
    "127.0.0.1 0.0.0.0",   # mixed: one loopback doesn't save an exposed bind
    "0.0.0.0 ::1",
    "host.example.com",
])
def test_loopback_bound_fails_closed_on_exposed_bind(monkeypatch, bind):
    monkeypatch.setenv("APP_BIND", bind)
    assert is_loopback_bound() is False


# ── task router wires the gate into the unconfigured-admin branch ─────────

def test_task_routes_is_admin_consults_loopback_gate():
    src = Path(__file__).resolve().parent.parent.joinpath("routes", "task_routes.py").read_text()
    # The unconfigured branch must (a) respect the loopback gate and (b) not
    # blindly return True. Confirms the closure hardens rather than reverting
    # to the old fail-open `return True`.
    assert "is_loopback_bound()" in src
    assert "from core.middleware import INTERNAL_TOOL_USER, is_loopback_bound" in src
    # Sanity: the old unconditional-trust line must be gone.
    assert "Unconfigured single-user deploy: trust the local owner." not in src