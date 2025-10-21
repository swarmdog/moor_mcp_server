# WARNING

Use at your own risk.  

# mooR MCP Server (FastMCP)

Expose mooR's REST automation surface as Model Context Protocol (MCP) tools so agents can authenticate, inspect, and edit a running mooR world.

Repo for mooR (LambdaMOO server): https://github.com/rdaum/moor

## Tips

When using with an assistant such as Cursor, AugmentCode, you can provide multiple sets of MOO credentials via agents.md or similar, allowing the assistant to switch between wizard/programmer/player for testing.

<img width="1468" height="1042" alt="moormcp" src="https://github.com/user-attachments/assets/027ef0f9-5d36-45ae-b957-6b4eb35a8a9b" />

## Requirements
- Python 3.10+
- Docker (optional)

## Install (local)
```bash
python -m venv .venv
# PowerShell: .venv\\Scripts\\Activate.ps1 | Bash: source .venv/bin/activate
pip install -r requirements.txt
```

## Configure
Set environment variables (defaults shown):
- `MOOR_BASE_URL` (`http://localhost:8081`)
- `MOOR_PLAYER`
- `MOOR_PASSWORD`
- `MCP_HOST` (`127.0.0.1`)
- `MCP_PORT` (`8085`)

## Run (local)
HTTP transport (default):
```bash
python -m main run --host 0.0.0.0 --port 8085
```
Stdio transport:
```bash
python -m main --transport stdio
```
Debug tools list (HTTP): open http://127.0.0.1:8085/debug/tools

## Docker
Build image:
```bash
docker build -t moor-mcp-server .
```
Run container (HTTP):
```bash
docker run --rm -p 8085:8085 \
  -e MOOR_BASE_URL=http://host.docker.internal:8081 \
  -e MOOR_PLAYER=YourUser -e MOOR_PASSWORD=YourPass \
  moor-mcp-server
```
Notes:
- Dockerfile entrypoint is `python -m main` with default command `run`.
- The image sets `MCP_HOST=0.0.0.0` and `MCP_PORT=8085` so the server binds externally.
- Override args if needed, e.g.: `docker run ... moor-mcp-server run --host 0.0.0.0 --port 8085`.

## Tools (selection)
- `moor_connect_auth`, `moor_eval_expr`
- `moor_resolve_object`, `moor_create_object`
- `moor_list_properties`, `moor_get_property`, `moor_set_property`
- `moor_list_verbs`, `moor_get_verb`, `moor_ensure_verb`, `moor_program_verb`, `moor_invoke_verb`
- `moor_get_history`
