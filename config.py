from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    """Runtime configuration for the MCP server."""

    base_url: str = "http://localhost:8081"
    default_player: Optional[str] = None
    default_password: Optional[str] = None
    host: str = "127.0.0.1"
    port: int = 8085

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("MOOR_BASE_URL", cls.base_url)
        player = os.getenv("MOOR_PLAYER")
        password = os.getenv("MOOR_PASSWORD")
        host = os.getenv("MCP_HOST", cls.host)
        port = int(os.getenv("MCP_PORT", str(cls.port)))
        return cls(base_url=base_url, default_player=player, default_password=password, host=host, port=port)
