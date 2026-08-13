from __future__ import annotations

import anyio
import pytest
from integrations.reins import mcp_client


class TransportReachedError(RuntimeError):
    pass


def test_call_tool_fails_before_transport_when_vault_token_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    client_calls: list[dict[str, str] | None] = []

    def unexpected_client(headers: dict[str, str] | None = None) -> None:
        client_calls.append(headers)
        raise AssertionError("HTTP client created without a token")

    monkeypatch.setattr(mcp_client, "_load_http_token", lambda: None)
    monkeypatch.setattr(mcp_client, "create_mcp_http_client", unexpected_client)

    # When / Then
    with pytest.raises(mcp_client.MissingMcpHttpTokenError):
        _ = anyio.run(mcp_client.call_tool, "trail_list")
    assert client_calls == []


def test_call_tool_sends_vault_token_as_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    captured_headers: list[dict[str, str] | None] = []

    def capture_client(headers: dict[str, str] | None = None) -> None:
        captured_headers.append(headers)
        raise TransportReachedError("transport reached")

    monkeypatch.setattr(mcp_client, "_load_http_token", lambda: "vault-token")
    monkeypatch.setattr(mcp_client, "create_mcp_http_client", capture_client)

    # When / Then
    with pytest.raises(TransportReachedError, match="transport reached"):
        _ = anyio.run(mcp_client.call_tool, "trail_list")
    assert captured_headers == [{"Authorization": "Bearer vault-token"}]
