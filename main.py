
from __future__ import annotations

import typer

from config import Settings
from fastmcp_app import create_mcp


cli = typer.Typer(add_completion=False)


@cli.command()
def run(
    host: str = typer.Option(None, help="Host interface to bind (HTTP transport)."),
    port: int = typer.Option(None, help="Port to bind (HTTP transport)."),
    transport: str = typer.Option("http", help="Transport: 'http' or 'stdio'."),
) -> None:
    """Start the FastMCP server (defaults to HTTP transport)."""

    settings = Settings.from_env()
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port

    mcp = create_mcp(settings)
    if transport == "stdio":
        mcp.run()
    else:
        # Force JSON-style HTTP on /mcp (non-streaming)
        app = mcp.http_app(path="/mcp", transport="http", json_response=True, stateless_http=True)
        import uvicorn
        uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


@cli.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run()


if __name__ == "__main__":
    cli()
