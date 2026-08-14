"""Regression tests: research session_id must reject path-traversal sequences."""

import re

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9-]{1,128}$")


def test_accepts_rp_prefixed_id():
    assert _SESSION_ID_RE.fullmatch("rp-abc123def456") is not None


def test_accepts_standard_uuid():
    assert _SESSION_ID_RE.fullmatch("550e8400-e29b-41d4-a716-446655440000") is not None


def test_accepts_custom_alphanumeric():
    assert _SESSION_ID_RE.fullmatch("custom-id-123") is not None


def test_rejects_double_dot():
    assert _SESSION_ID_RE.fullmatch("..") is None


def test_rejects_single_dot():
    assert _SESSION_ID_RE.fullmatch(".") is None


def test_rejects_dot_slash_traversal():
    assert _SESSION_ID_RE.fullmatch("../../data/auth") is None


def test_rejects_deep_traversal():
    assert _SESSION_ID_RE.fullmatch("../../../etc/passwd") is None


def test_rejects_mixed_traversal():
    assert _SESSION_ID_RE.fullmatch("normal/../../traversal") is None


def test_rejects_dot_prefix_traversal():
    assert _SESSION_ID_RE.fullmatch("./../../secret") is None


def test_rejects_empty():
    assert _SESSION_ID_RE.fullmatch("") is None


def test_rejects_whitespace():
    assert _SESSION_ID_RE.fullmatch(" ") is None


def test_rejects_slash():
    assert _SESSION_ID_RE.fullmatch("a/b") is None


def test_rejects_null_byte():
    assert _SESSION_ID_RE.fullmatch("rp-test\x00") is None
