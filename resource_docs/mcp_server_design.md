# mooR MCP Server Design

## Overview
The mooR MCP server packages mooR's REST automation surface as a [Model Context Protocol](https://modelcontextprotocol.io/) endpoint. It allows agents to authenticate against a live mooR shard, inspect objects, manipulate verbs, and retrieve curated documentation without relying on telnet sessions.

## Package layout
```
moor_mcp_server/
├── __init__.py        # Exports: Settings, create_mcp
├── config.py          # Settings dataclass populated from environment variables
├── fastmcp_app.py     # FastMCP server factory and tool/resource/route registration
├── main.py            # Typer CLI (HTTP via uvicorn, or stdio)
├── prompts.py         # Prompt registry exposed via MCP
├── resources.py       # Markdown resource registry
├── resource_docs/     # Packaged documentation
└── rest_client.py     # HTTP helper for mooR REST endpoints and verb tooling
```

## Configuration flow
`config.Settings` collects runtime configuration in a dataclass:

- `base_url` – REST entry point for the running mooR shard (defaults to `http://localhost:8081`).
- `default_player` / `default_password` – Credentials used for lazy authentication.
- `host` / `port` – Interface and port the MCP HTTP server binds to when using HTTP transport.

`Settings.from_env()` reads `MOOR_BASE_URL`, `MOOR_PLAYER`, `MOOR_PASSWORD`, `MCP_HOST`, and `MCP_PORT`, falling back to sensible defaults so the packaged server only requires environment variables or CLI overrides.

## REST client
`rest_client.MoorRestClient` wraps `requests.Session` and centralises authentication and error handling for the mooR REST API.

- The first tool call that requires authentication triggers `connect()`, which POSTs to `/auth/connect` and caches the returned `X-Moor-Auth-Token`. 401 responses automatically retry once after refreshing credentials.
- `_request()` normalises timeouts and converts HTTP failures into `MoorRestClientError` exceptions that include the status code and decoded payload when available.
- Helper methods such as `create_object`, `set_property`, `ensure_verb`, `program_verb`, and `invoke_verb` translate JSON arguments into valid MOO literals before delegating to `_request()`.
- Utility helpers (`_curie_to_moo_expr`, `_json_to_moo_literal`) manage CURIE resolution (`oid:*`, `sysobj:*`, `match("…")`) and safe string escaping so tool handlers do not need to reason about MOO syntax.


### Authentication workflow and error taxonomy
- Tokens are cached in memory only; on server restart, users must re‑authenticate (e.g., by calling `moor_connect_auth`).
- Structured auth errors raised by the REST client:
  - `AuthenticationRequired` (missing credentials). Includes a resolution hint to call `moor_connect_auth(player, password)`.
  - `InvalidCredentials` (401 from `/auth/connect`).
  - `TokenExpired` (401 after one automatic retry during an authenticated request).
- The `moor_connect_auth` tool returns `{ "ok": true, "player": "<player>" }` and never returns the token. The token is stored only in memory in the server process.
- A `moor_disconnect_auth` tool clears the in‑memory token (and optionally defaults when requested).

Because every MCP tool delegates to this client, handler implementations remain thin wrappers that validate input and format responses.

## Tools (FastMCP)
Tools are registered via `@FastMCP.tool` decorators in `fastmcp_app.py` under `moor_*` names for consistency. Examples include:

- `moor_connect_auth`, `moor_disconnect_auth`, `moor_eval_expr`
- `moor_create_object`, `moor_set_property`, `moor_list_properties`, `moor_get_property`
- `moor_list_verbs`, `moor_get_verb`, `moor_ensure_verb`, `moor_program_verb`, `moor_invoke_verb`
- `moor_resolve_object`, `moor_get_history`
- `moor_list_presentations`, `moor_dismiss_presentation`, `moor_list_sysobjs`

Debug HTTP routes are also provided (e.g., `/debug/tools`) for quick inspection during local development.

## Resource registry
`resources.ResourceRegistry` exposes packaged documentation to MCP clients. The current package registers:

- `moor-doc://mcp-design` → `mcp_server_design.md`
- `moor-doc://moo-programming` → `moo_programming_quickstart.md`

Adding new markdown files under `resource_docs/` and wiring them in `resources.py` makes them available to clients.

## Prompt registry
`prompts.PromptRegistry` publishes lightweight prompts that walk agents through common maintenance tasks (authenticating, programming verbs, staging rooms, managing presentations, etc.).

## Server wiring (FastMCP)
`fastmcp_app.create_mcp()` wires the components together:

1. Load settings and construct the shared `MoorRestClient`.
2. Register tools (decorators), resources, and lightweight debug routes on a `FastMCP` instance.
3. Return the configured `FastMCP` object.

The server can run in two modes:
- HTTP: `mcp.http_app(path="/mcp", transport="http", json_response=True, stateless_http=True)` (serve with `uvicorn`).
- stdio: `mcp.run()`

## CLI entry point
`main.py` provides a Typer CLI wrapper so operators can launch the server with a single command:

```bash
python -m main run --host 0.0.0.0 --port 8085     # HTTP
python -m main --transport stdio                   # stdio
```

The command loads environment-driven defaults via `Settings.from_env()`, allows explicit host/port overrides, and then starts the selected transport.

## Testing and extension points
The codebase is designed for straightforward testing—`create_mcp()` accepts injected clients, and modules are small and composable. Future enhancements can add more packaged documentation, extend the prompt catalogue, or stream history updates while keeping the distribution self-contained.
