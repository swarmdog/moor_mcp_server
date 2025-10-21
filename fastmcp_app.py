from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from fastmcp import FastMCP

from _prop_utils import extract_obj_curie
from config import Settings
from rest_client import MoorRestClient, MoorRestClientError, _json_to_moo_literal


def create_mcp(settings: Optional[Settings] = None, rest_client: Optional[MoorRestClient] = None) -> FastMCP:
    """Create and configure a FastMCP server exposing mooR automation tools.

    Tools are registered with moor_* names for compatibility with mooR-based agent
    guidelines. 
    """
    cfg = settings or Settings.from_env()
    client = rest_client or MoorRestClient(
        base_url=cfg.base_url,
        default_player=cfg.default_player,
        default_password=cfg.default_password,
    )

    mcp = FastMCP(name="mooR MCP Server")

    # Keep references to decorated Tool objects for debug/introspection
    registered_tool_objs: list[Any] = []



    # Debug route to inspect tool registration via HTTP
    @mcp.custom_route("/debug/tools", methods=["GET"])
    async def debug_tools(request):  # type: ignore[no-redef]
        try:
            from starlette.responses import JSONResponse, PlainTextResponse
            tool_names = sorted({getattr(t, 'name', '') for t in registered_tool_objs if getattr(t, 'name', '')})
            return JSONResponse({"tools": tool_names})
        except Exception as e:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(str(e), status_code=500)

    @mcp.custom_route("/debug/ping2", methods=["GET"])
    async def debug_ping2(request):  # type: ignore[no-redef]
        try:
            from starlette.responses import JSONResponse
            names = [getattr(t, 'name', '') for t in registered_tool_objs]
            return JSONResponse({"count": len(registered_tool_objs), "names": names[:5]})
        except Exception as e:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse(str(e), status_code=500)



    # ---------------------------- Tools ---------------------------------



    @mcp.tool(name="moor_connect_auth")
    def moor_connect_auth(player: str, password: str) -> dict:
        client.connect(player=player, password=password)
        return {"ok": True, "player": player}
    registered_tool_objs.append(moor_connect_auth)

    @mcp.tool(name="moor_disconnect_auth")
    def moor_disconnect_auth(clear_defaults: bool = False) -> dict:
        client.auth_token = None
        if clear_defaults:
            client.default_player = None
            client.default_password = None
        return {"ok": True}
    registered_tool_objs.append(moor_disconnect_auth)


    @mcp.tool(name="moor_eval_expr")
    def moor_eval_expr(expression: str) -> Any:
        return client.eval_expr(expression)
    registered_tool_objs.append(moor_eval_expr)


    @mcp.tool(name="moor_create_object")
    def moor_create_object(parent: str, owner: str, properties: Optional[dict] = None) -> Any:
        return client.create_object(parent, owner, properties)
    registered_tool_objs.append(moor_create_object)


    @mcp.tool(name="moor_set_property")
    def moor_set_property(object: str, property: str, value: Any) -> Any:  # noqa: A002 - MCP arg name compatibility
        return client.set_property(object, property, value)
    registered_tool_objs.append(moor_set_property)


    @mcp.tool(name="moor_list_properties")
    def moor_list_properties(object: str, inherited: bool = False) -> Any:  # noqa: A002
        return client.list_properties(object, inherited)
    registered_tool_objs.append(moor_list_properties)


    @mcp.tool(name="moor_get_property")
    def moor_get_property(object: str, property: str) -> Any:  # noqa: A002
        return client.get_property(object, property)
    registered_tool_objs.append(moor_get_property)


    @mcp.tool(name="moor_list_verbs")
    def moor_list_verbs(object: str, inherited: bool = False) -> Any:  # noqa: A002
        return client.list_verbs(object, inherited)
    registered_tool_objs.append(moor_list_verbs)


    @mcp.tool(name="moor_get_verb")
    def moor_get_verb(object: str, verb_name: str) -> Any:  # noqa: A002
        return client.get_verb(object, verb_name)
    registered_tool_objs.append(moor_get_verb)


    @mcp.tool(name="moor_ensure_verb")
    def moor_ensure_verb(
        object: str,  # noqa: A002
        verb_name: str,
        owner_expr: str = "player",
        perms: str = "rxd",
        args: Optional[List[str]] = None,
    ) -> dict:
        client.ensure_verb(object, verb_name, owner_expr=owner_expr, perms=perms, args=args)
        return {"ok": True}
    registered_tool_objs.append(moor_ensure_verb)


    @mcp.tool(name="moor_program_verb")
    def moor_program_verb(
        object: str,  # noqa: A002
        verb_name: str,
        code: str,
        owner_expr: str = "player",
        perms: str = "rxd",
        args: Optional[List[str]] = None,
    ) -> Any:
        client.ensure_verb(object, verb_name, owner_expr=owner_expr, perms=perms, args=args)
        return client.program_verb(object, verb_name, code)
    registered_tool_objs.append(moor_program_verb)


    @mcp.tool(name="moor_invoke_verb")
    def moor_invoke_verb(object: str, verb_name: str, args: Optional[List[Any]] = None) -> Any:  # noqa: A002
        return client.invoke_verb(object, verb_name, args or [])
    registered_tool_objs.append(moor_invoke_verb)


    @mcp.tool(name="moor_resolve_object")
    def moor_resolve_object(object: str) -> str:  # noqa: A002
        curie = client.resolve_object(object)
        if not isinstance(curie, str):
            raise MoorRestClientError("object could not be resolved", status_code=404)
        return curie
    registered_tool_objs.append(moor_resolve_object)


    @mcp.tool(name="moor_get_history")
    def moor_get_history(since_seconds: Optional[int] = None, limit: Optional[int] = None) -> Any:
        return client.get_history(since_seconds=since_seconds, limit=limit)
    registered_tool_objs.append(moor_get_history)


    # Optional extras preserved from legacy server
    @mcp.tool(name="moor_list_presentations")
    def moor_list_presentations() -> Any:
        return client.list_presentations()
    registered_tool_objs.append(moor_list_presentations)

    @mcp.tool(name="moor_list_sysobjs")
    def moor_list_sysobjs(names: Optional[List[str]] = None) -> Any:
        """Return a mapping of sysobj names to object CURIEs.

        Refactored to a single batched eval call to avoid N+1 REST requests.
        Behavior parity:
        - If names provided: include all requested names; values are CURIEs or None.
        - If names omitted: include only properties on #0 whose values are objects.
        """
        # Build a single MOO program that returns a list of {name, value} pairs where
        # value is either an object reference or 0. We'll translate that to {name: curie|None}.
        if names:
            names_literal = _json_to_moo_literal(names)
            names_stmt = f"names = {names_literal};"
            include_all = True
        else:
            names_stmt = "names = properties(#0);"
            include_all = False

        lines = [
            names_stmt,
            "out = {};",
            "for n in (names)",
            "  try",
            "    v = #0.(n);",
            "  except error (ANY)",
            "    v = 0;",
            "  endtry;",
            "  if (typeof(v) == OBJ)",
            "    out = {@out, {n, v}};",
            f"  elseif ({'1' if include_all else '0'})",
            "    out = {@out, {n, 0}};",
            "  endif;",
            "endfor;",
            "return out;",
        ]
        program = "\n".join(lines)

        payload = client.eval_expr(program)

        # Convert list-of-pairs into {name: curie|None}
        result: dict[str, Optional[str]] = {}
        if isinstance(payload, list):
            for item in payload:
                if (
                    isinstance(item, list)
                    and len(item) == 2
                    and isinstance(item[0], str)
                ):
                    name = item[0]
                    value = item[1]
                    curie = extract_obj_curie(value)
                    result[name] = curie if curie else None
        return result
    registered_tool_objs.append(moor_list_sysobjs)



    @mcp.tool(name="moor_dismiss_presentation")
    def moor_dismiss_presentation(presentation_id: str) -> Any:
        return client.dismiss_presentation(presentation_id)
    registered_tool_objs.append(moor_dismiss_presentation)


    @mcp.tool(name="moor_move_object")
    def moor_move_object(object: str, destination: str) -> Any:  # noqa: A002
        return client.move_object(object, destination)
    registered_tool_objs.append(moor_move_object)


    @mcp.tool(name="moor_recycle_object")
    def moor_recycle_object(object: str) -> Any:  # noqa: A002
        return client.recycle_object(object)
    registered_tool_objs.append(moor_recycle_object)


    # ------------------------- Resources/Prompts ------------------------
    # Provide doc resources via resource URIs using standalone-safe paths
    package_root = Path(__file__).parent
    resource_docs_dir = package_root / "resource_docs"

    def _read(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    @mcp.resource("moor-doc://mcp-design")
    def resource_mcp_design() -> str:
        return _read(resource_docs_dir / "mcp_server_design.md")

    @mcp.resource("moor-doc://moo-programming")
    def resource_moo_programming() -> str:
        return _read(resource_docs_dir / "moo_programming_quickstart.md")

    return mcp

