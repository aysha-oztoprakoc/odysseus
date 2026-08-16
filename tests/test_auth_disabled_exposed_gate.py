"""Regression tests for the AUTH_ENABLED=false network-exposed gate.

Audit/deployment footgun: binding an auth-disabled Odysseus instance to a
non-loopback address silently disables authentication for every remote caller.
``gate_auth_disabled_exposed`` (core/middleware.py) refuses to boot unless the
operator explicitly confirms that config -- an interactive first-run prompt on a
TTY, or the ``ODYSSEUS_ALLOW_AUTH_DISABLED_EXPOSED=1`` sentinel for
non-interactive (systemd/docker/CI) launches. Loopback-bound auth-disabled
startups (single-user local dev) pass through untouched.
"""

import core.middleware as mw


def _run(bind, auth, sentinel=None, isatty=False, answers=None):
    """Exercise the gate with controlled env + stdin simulation."""
    import os
    from unittest import mock

    if auth is None:
        os.environ.pop("AUTH_ENABLED", None)
    else:
        os.environ["AUTH_ENABLED"] = auth
    if sentinel is None:
        os.environ.pop(mw.AUTH_DISABLED_CONFIRM_ENV, None)
    else:
        os.environ[mw.AUTH_DISABLED_CONFIRM_ENV] = sentinel

    stdin = mock.MagicMock()
    stdin.isatty.return_value = isatty
    if answers is None:
        stdin.read.return_value = ""
    # simulate the builtin input() reading from our fake stdin line by line
    input_iter = iter(answers or [])
    def fake_input(_prompt=""):
        return next(input_iter, "")
    with mock.patch.object(mw, "input", side_effect=fake_input), \
         mock.patch.object(mw.sys, "stdin", stdin):
        return mw.gate_auth_disabled_exposed(bind)


def test_auth_enabled_always_passes():
    """Auth on (default) is never gated, even when network-exposed."""
    assert _run("0.0.0.0", auth="true") is True
    assert _run("0.0.0.0", auth=None) is True


def test_auth_disabled_loopback_passes_no_prompt():
    """Loopback single-user mode is untouched, even non-interactive."""
    assert _run("127.0.0.1", auth="false", isatty=False) is True
    assert _run("::1", auth="false", isatty=False) is True
    assert _run("localhost", auth="false", isatty=False) is True


def test_auth_disabled_exposed_refuses_noninteractive_without_sentinel():
    """Network-exposed + auth-disabled + no TTY + no sentinel -> fail closed."""
    assert _run("0.0.0.0", auth="false", isatty=False) is False
    assert _run("192.168.1.10", auth="false", isatty=False) is False


def test_auth_disabled_exposed_ok_with_sentinel():
    """Env sentinel permits non-interactive network-exposed auth-disabled."""
    assert _run(
        "0.0.0.0", auth="false", sentinel="1", isatty=False
    ) is True
    assert _run(
        "0.0.0.0", auth="false", sentinel="true", isatty=False
    ) is True
    assert _run(
        "198.51.100.4", auth="false", sentinel="yes", isatty=False
    ) is True


def test_auth_disabled_exposed_tty_confirm():
    """Typing 'DISABLE' on a TTY confirms auth-disabled exposed startup."""
    assert _run("0.0.0.0", auth="false", isatty=True, answers=["DISABLE"]) is True


def test_auth_disabled_exposed_tty_refuse():
    """Anything but 'DISABLE' on a TTY aborts."""
    assert _run("0.0.0.0", auth="false", isatty=True, answers=["no"]) is False
    assert _run("0.0.0.0", auth="false", isatty=True, answers=[""]) is False