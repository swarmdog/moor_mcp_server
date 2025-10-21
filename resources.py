from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from config import Settings


@dataclass
class ResourceDefinition:
    uri: str
    description: str
    path: Path

    def as_metadata(self) -> Dict[str, str]:
        return {"uri": self.uri, "description": self.description}

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")


class ResourceRegistry:
    def __init__(self, settings: Settings) -> None:
        root = package_root = Path(__file__).parent.absolute()
        resources_dir = package_root / "resource_docs"
        definitions: Iterable[Tuple[str, str, Path]] = (
            (
                "moor-doc://mcp-design",
                "mooR MCP Server Design",
                resources_dir / "mcp_server_design.md",
            ),
            (
                "moor-doc://moo-programming",
                "MOO Programming Quickstart",
                resources_dir / "moo_programming_quickstart.md",
            ),
        )

        self._resources: Dict[str, ResourceDefinition] = {}
        for uri, description, path in definitions:
            self._register(ResourceDefinition(uri=uri, description=description, path=path))

    def _register(self, definition: ResourceDefinition) -> None:
        if definition.path.exists():
            self._resources[definition.uri] = definition

    def list_resources(self) -> List[Dict[str, str]]:
        return [definition.as_metadata() for definition in self._resources.values()]

    def read_resource(self, uri: str) -> str:
        definition = self._resources.get(uri)
        if not definition:
            raise FileNotFoundError(uri)
        return definition.read()
