from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ResourceSpec:
    uri: str
    description: str
    filename: str


RESOURCE_CATALOG: Tuple[ResourceSpec, ...] = (
    ResourceSpec(
        uri="moor-doc://mcp-design",
        description="Design blueprint for the mooR MCP server.",
        filename="mcp_server_design.md",
    ),
    ResourceSpec(
        uri="moor-doc://moo-programming",
        description="Primer on programming verbs and tasks in mooR.",
        filename="moo_programming_quickstart.md",
    ),
)


__all__ = ["ResourceSpec", "RESOURCE_CATALOG"]
