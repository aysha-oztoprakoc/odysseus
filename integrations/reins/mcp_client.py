"""
Thin async client for the data_rein harness's `reins` MCP server, reached over
streamable-HTTP (Odysseus runs in Docker with no stdio pipe to the host - see
`reins.harness.mcp_server.main(http=True)` on the data_rein side, started by
`reins ody start`).

This is the ONLY place Odysseus talks to data_rein - every dashboard route in
`routes/reins_routes.py` calls `call_tool()` here rather than importing the
`reins` package directly (which isn't installed/mountable in this container).
"""

from __future__ import annotations

import os
from typing import Final

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import TextContent
from pydantic import JsonValue, TypeAdapter, ValidationError

REINS_MCP_URL = os.environ.get("REINS_MCP_URL", "http://host.docker.internal:8765/mcp")
_JSON_VALUE_ADAPTER: Final[TypeAdapter[JsonValue]] = TypeAdapter(JsonValue)
_TEXT_CONTENT_ADAPTER: Final[TypeAdapter[TextContent]] = TypeAdapter(TextContent)


class MissingMcpHttpTokenError(RuntimeError):
    pass


def _load_http_token() -> str | None:
    from scripts.get_secrets import get_secret

    return get_secret("REINS_MCP_HTTP_TOKEN")


async def call_tool(name: str, **kwargs: JsonValue) -> JsonValue:
    """Call one `reins` MCP tool and return its parsed JSON result.

    Every `reins` MCP tool returns a JSON string (see mcp_server.py), so this
    parses JSON through the typed boundary and falls back to raw text if a tool
    ever returns something else. Raises on connection/tool failure - callers
    (route handlers) are responsible for catching and degrading gracefully,
    since "the harness MCP server is unreachable" is a real, expected state
    (e.g. before `reins ody start` has run).
    """
    token = _load_http_token()
    if not token:
        raise MissingMcpHttpTokenError(
            "encrypted vault secret REINS_MCP_HTTP_TOKEN is required for HTTP MCP"
        )
    headers = {"Authorization": f"Bearer {token}"}
    async with (
        create_mcp_http_client(headers=headers) as http_client,
        streamable_http_client(REINS_MCP_URL, http_client=http_client) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
        _ = await session.initialize()
        result = await session.call_tool(name, kwargs)
        if not result.content:
            return {}
        try:
            text = _TEXT_CONTENT_ADAPTER.validate_python(result.content[0]).text
        except ValidationError:
            return {}
        try:
            return _JSON_VALUE_ADAPTER.validate_json(text)
        except ValueError:
            return text
