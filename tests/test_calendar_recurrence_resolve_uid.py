"""Regression tests for calendar recurrence base UID resolution."""

import pytest

from tests.helpers.calendar_routes import import_calendar_routes


# ── _resolve_base_uid ──────────────────────────────────────────────────

def test_resolve_base_uid_plain_passthrough():
    cal = import_calendar_routes()
    assert cal._resolve_base_uid("evt-123") == "evt-123"


def test_resolve_base_uid_compound_strips_suffix_date():
    cal = import_calendar_routes()
    assert cal._resolve_base_uid("evt-123::2026-06-15") == "evt-123"


def test_resolve_base_uid_compound_strips_suffix_datetime():
    cal = import_calendar_routes()
    assert cal._resolve_base_uid("evt-123::2026-06-15T09:00") == "evt-123"


def test_resolve_base_uid_rejects_empty():
    cal = import_calendar_routes()
    with pytest.raises(ValueError, match="empty uid"):
        cal._resolve_base_uid("")


def test_resolve_base_uid_rejects_missing_base():
    cal = import_calendar_routes()
    with pytest.raises(ValueError, match="malformed compound UID"):
        cal._resolve_base_uid("::2026-06-15")
