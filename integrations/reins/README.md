# data_rein Harness Integration

Unlike the `claude`/`codex` integrations in this directory (which let *other*
agents install an Odysseus-provided plugin), this one is the reverse: it
registers data_rein's own `reins` MCP server as an **external** MCP server
inside Odysseus, so Odysseus's own chat/agent features get first-class,
conversational access to the harness's wiki, task trail, model router, and
token budgets — the same tools (`wiki_search`, `trail_list`, `route_local`,
`escalate_cloud`, `agent_budgets`, `set_agent_budget`, `token_usage_status`,
etc.) that Claude Code, OpenCode, and Antigravity already call.

This is separate from the **Harness dashboard** (the "Harness" icon-rail
button) — that's a dedicated read/write UI (`static/js/harness.js`,
`routes/reins_routes.py`) for humans. This integration is for Odysseus's
*own* chat agent to reach the same data conversationally.

## Prerequisite

`reins ody start` (in the main data_rein repo) already starts
`reins mcp --http --port 8765` before bringing Odysseus's containers up — the
server should already be reachable at `http://host.docker.internal:8765/mcp`
from inside the Odysseus container. Streamable HTTP always requires the
`REINS_MCP_HTTP_TOKEN` entry in data_rein's encrypted vault. Both the server and
Odysseus read that entry through `scripts.get_secrets.get_secret`; there is no
environment-variable or plaintext fallback. The Odysseus container therefore
needs read-only access to the harness `scripts/get_secrets.py`, `.secrets.key`,
and `.secrets.enc` paths.

An unauthenticated probe confirms the protection is active:

```bash
curl http://127.0.0.1:8765/mcp   # 401 means the authenticated endpoint is up
```

## Registering it (one-time, manual)

This is a manual setup step rather than a programmatic one — seeding
Odysseus's `McpServer` database table from an integration script would be
fragile against upstream schema changes in this vendored app. Instead, use
Odysseus's own admin UI:

1. Open Odysseus → Settings → Integrations → MCP Servers.
2. Add a new server:
   - **Name**: `reins`
   - **Transport**: `http`
   - **URL**: `http://host.docker.internal:8765/mcp`
   - **Authorization**: `Bearer` with the vault-backed MCP token
3. Save. Odysseus should connect and list the tools above under that server.

(Equivalent API call, if you'd rather script it — still requires an admin
session cookie: `POST /api/mcp/servers` with form fields `name=reins`,
`transport=http`, `url=http://host.docker.internal:8765/mcp` — see
`routes/mcp_routes.py`'s `add_server`.)
