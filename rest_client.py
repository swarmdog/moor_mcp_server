
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests

DEFAULT_TIMEOUT = 30


def _escape_moo_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _json_to_moo_literal(value: Any) -> str:
    if value is None:
        return "0"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _escape_moo_string(value)
    if isinstance(value, list):
        elements = ", ".join(_json_to_moo_literal(v) for v in value)
        inside = f" {elements} " if elements else ""
        return "{" + inside + "}"
    if isinstance(value, dict):
        pairs: List[str] = []
        for key, item in value.items():
            pairs.append("{" + _json_to_moo_literal(key) + ", " + _json_to_moo_literal(item) + "}")
        inside = ", ".join(pairs)
        inner = f" {inside} " if inside else ""
        return "{" + inner + "}"
    return _escape_moo_string(str(value))


@dataclass
class MoorRestClientError(Exception):
    message: str
    status_code: Optional[int] = None
    details: Optional[Any] = None
    code: Optional[str] = None
    resolution: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - logging helper
        base = self.message
        if self.code:
            base = f"[{self.code}] " + base
        if self.status_code is not None:
            base += f" (status={self.status_code})"
        if self.details is not None:
            base += f": {self.details}"
        if self.resolution:
            base += f" | resolution: {self.resolution}"
        return base


class MoorRestClient:
    """Standalone REST helper for mooR automation."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        default_player: Optional[str] = None,
        default_password: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("MOOR_BASE_URL") or "http://localhost:8081").rstrip("/")
        self.default_player = default_player or os.getenv("MOOR_PLAYER")
        self.default_password = default_password or os.getenv("MOOR_PASSWORD")
        self.timeout = timeout
        self._session = session or requests.Session()
        self.auth_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------
    def connect(self, player: Optional[str] = None, password: Optional[str] = None) -> str:
        player_name = player or self.default_player
        pw = password or self.default_password
        if not player_name or not pw:
            raise MoorRestClientError(
                "player and password must be provided for authentication",
                code="AuthenticationRequired",
                resolution="Call moor_connect_auth(player, password)",
            )

        url = f"{self.base_url}/auth/connect"
        resp = self._session.post(url, data={"player": player_name, "password": pw}, timeout=self.timeout)
        details = self._response_details(resp)
        if resp.status_code == 401:
            raise MoorRestClientError(
                "invalid credentials",
                status_code=resp.status_code,
                details=details,
                code="InvalidCredentials",
                resolution="Verify player/password and call moor_connect_auth again",
            )
        if resp.status_code >= 400:
            raise MoorRestClientError(
                "authentication failed",
                status_code=resp.status_code,
                details=details,
                code="AuthFailed",
            )
        token = resp.headers.get("X-Moor-Auth-Token")
        if not token:
            raise MoorRestClientError(
                "authentication succeeded but no X-Moor-Auth-Token header was returned",
                code="AuthProtocolError",
            )

        self.auth_token = token.strip()
        self.default_player = player_name
        self.default_password = pw
        return self.auth_token

    def ensure_auth(self) -> None:
        if not self.auth_token:
            self.connect()

    def _headers(self) -> Dict[str, str]:
        if not self.auth_token:
            raise MoorRestClientError("not authenticated; call connect first")
        return {
            "X-Moor-Auth-Token": self.auth_token,
            "Accept": "application/json",
        }

    def _response_details(self, resp: requests.Response) -> Any:
        if resp.content:
            try:
                return resp.json()
            except ValueError:
                return resp.text
        return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        context: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        requires_auth: bool = True,
        none_statuses: Iterable[int] = (),
        allow_empty: bool = False,
    ) -> Any:
        attempt = 0
        while True:
            if requires_auth:
                self.ensure_auth()
            req_headers: Dict[str, str] = {}
            if requires_auth:
                req_headers.update(self._headers())
            if headers:
                req_headers.update(headers)
            resp = self._session.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                data=data,
                headers=req_headers or None,
                timeout=self.timeout,
            )
            if (
                resp.status_code == 401
                and requires_auth
                and attempt == 0
                and self.default_player
                and self.default_password
            ):
                attempt += 1
                self.auth_token = None
                continue
            break

        if resp.status_code in set(none_statuses):
            return None
        if resp.status_code >= 400:
            details = self._response_details(resp)
            if resp.status_code == 401 and requires_auth:
                code = "TokenExpired" if attempt > 0 else "AuthenticationRequired"
                resolution = "Call moor_connect_auth(player, password)"
                raise MoorRestClientError(
                    "authentication required or token invalid",
                    status_code=resp.status_code,
                    details=details,
                    code=code,
                    resolution=resolution,
                )
            raise MoorRestClientError(
                f"mooR API request failed during {context}",
                status_code=resp.status_code,
                details=details,
            )
        if not resp.content:
            return {} if allow_empty else None
        try:
            payload: Any = resp.json()
        except ValueError:
            payload = resp.text
        return self._ensure_no_moo_errors(payload, context=context)

    def _ensure_no_moo_errors(self, payload: Any, *, context: str) -> Any:
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                raise MoorRestClientError(
                    f"mooR reported errors during {context}",
                    status_code=400,
                    details=errors,
                )
            for key in ("error", "error_msg", "error_message"):
                value = payload.get(key)
                if value:
                    raise MoorRestClientError(
                        f"mooR reported errors during {context}",
                        status_code=400,
                        details=value,
                    )
        return payload

    # ------------------------------------------------------------------
    # Helpers for CURIEs / literals
    # ------------------------------------------------------------------
    def _encode_curie(self, object_curie: str) -> str:
        return quote((object_curie or "").strip(), safe=":.")

    def _curie_to_moo_expr(self, object_curie: str) -> str:
        curie = (object_curie or "").strip()
        if not curie:
            raise MoorRestClientError("object identifier must not be empty")
        if curie.startswith("#") or curie.startswith("$") or curie.startswith("match(\""):
            return curie
        if curie.startswith("oid:"):
            try:
                return f"#{int(curie.split(':', 1)[1])}"
            except Exception:
                return curie
        if curie.startswith("sysobj:"):
            ident = curie.split(':', 1)[1]
            return f"${ident}" if ident else curie
        if curie.startswith("uuid:"):
            return f"match(\"{curie}\")"
        return curie

    # ------------------------------------------------------------------
    # Public API wrappers
    # ------------------------------------------------------------------
    def eval_expr(self, expression: str) -> Any:
        expr = (expression or "").strip()
        if not expr:
            raise MoorRestClientError("expression must not be empty")
        if "\n" not in expr:
            if not re.search(r"\breturn\b", expr):
                expr = f"return {expr}" if not expr.startswith("return") else expr
            if not expr.rstrip().endswith(";"):
                expr = expr.rstrip() + ";"
        return self._request(
            "POST",
            "/eval",
            context="eval_expr",
            data=expr.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def create_object(
        self,
        parent_curie: str,
        owner_curie: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Any:
        parent_expr = self._curie_to_moo_expr(parent_curie)
        owner_expr = self._curie_to_moo_expr(owner_curie)
        lines: List[str] = [f"obj = create({parent_expr}, {owner_expr});"]
        if properties:
            for prop_name, value in properties.items():
                literal = _json_to_moo_literal(value)
                lines.append(f"obj.{prop_name} = {literal};")
        lines.append("return obj;")
        return self._request(
            "POST",
            "/eval",
            context="create_object",
            data="\n".join(lines).encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def set_property(self, object_curie: str, prop_name: str, value: Any) -> Any:
        target_expr = self._curie_to_moo_expr(object_curie)
        literal = _json_to_moo_literal(value)
        expr = f"{target_expr}.{prop_name} = {literal};\nreturn {target_expr}.{prop_name};"
        return self._request(
            "POST",
            "/eval",
            context="set_property",
            data=expr.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def list_properties(self, object_curie: str, inherited: bool = False) -> Any:
        return self._request(
            "GET",
            f"/properties/{self._encode_curie(object_curie)}",
            context="list_properties",
            params={"inherited": str(bool(inherited)).lower()},
        )

    def get_property(self, object_curie: str, prop_name: str) -> Any:
        return self._request(
            "GET",
            f"/properties/{self._encode_curie(object_curie)}/{prop_name}",
            context="get_property",
        )

    def list_verbs(self, object_curie: str, inherited: bool = False) -> Any:
        return self._request(
            "GET",
            f"/verbs/{self._encode_curie(object_curie)}",
            context="list_verbs",
            params={"inherited": str(bool(inherited)).lower()},
        )

    def get_verb(self, object_curie: str, verb_name: str) -> Any:
        return self._request(
            "GET",
            f"/verbs/{self._encode_curie(object_curie)}/{verb_name}",
            context="get_verb",
            none_statuses=(404,),
        )

    def ensure_verb(
        self,
        object_curie: str,
        verb_name: str,
        *,
        owner_expr: str = "player",
        perms: str = "rxd",
        args: Optional[Iterable[str]] = None,
    ) -> None:
        # Idempotency: if verb already exists, do nothing
        try:
            existing = self.get_verb(object_curie, verb_name)
            if isinstance(existing, dict):
                return
        except MoorRestClientError as e:
            if e.status_code not in (404, 500):
                raise
        dobj, prep, iobj = list(args) if args is not None else ["this", "none", "none"]
        target_expr = self._curie_to_moo_expr(object_curie)
        expr = (
            "try\n"
            f"  add_verb({target_expr}, {{{owner_expr}, \"{perms}\", \"{verb_name}\"}}, "
            f"{{\"{dobj}\", \"{prep}\", \"{iobj}\"}});\n"
            "except error (ANY)\n"
            "  0;\n"
            "endtry;\n"
            "return 1;"
        )
        self._request(
            "POST",
            "/eval",
            context="ensure_verb",
            data=expr.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def program_verb(self, object_curie: str, verb_name: str, code: str) -> Any:
        return self._request(
            "POST",
            f"/verbs/{self._encode_curie(object_curie)}/{verb_name}",
            context="program_verb",
            data=code.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def invoke_verb(self, object_curie: str, verb_name: str, args: Optional[List[Any]] = None) -> Any:
        return self._request(
            "POST",
            f"/verbs/{self._encode_curie(object_curie)}/{verb_name}/invoke",
            context="invoke_verb",
            json=args or [],
        )

    def resolve_object(self, object_curie: str) -> Optional[str]:
        result = self._request(
            "GET",
            f"/objects/{self._encode_curie(object_curie)}",
            context="resolve_object",
            none_statuses=(404,),
        )
        if not isinstance(result, dict):
            return None
        curie = result.get("obj") or result.get("oid") or result.get("object")
        return curie if isinstance(curie, str) else None

    def get_history(self, *, since_seconds: Optional[int] = None, limit: Optional[int] = None) -> Any:
        params: Dict[str, Any] = {}
        if since_seconds is not None:
            params["since_seconds"] = since_seconds
        if limit is not None:
            params["limit"] = limit
        return self._request(
            "GET",
            "/api/history",
            context="get_history",
            params=params or None,
        )

    def list_presentations(self) -> Any:
        return self._request("GET", "/api/presentations", context="list_presentations")

    def dismiss_presentation(self, presentation_id: str) -> Any:
        return self._request(
            "DELETE",
            f"/api/presentations/{presentation_id}",
            context="dismiss_presentation",
            allow_empty=True,
        )

    def move_object(self, object_curie: str, destination_curie: str) -> Any:
        obj_expr = self._curie_to_moo_expr(object_curie)
        dest_expr = self._curie_to_moo_expr(destination_curie)
        expr = f"move({obj_expr}, {dest_expr});\nreturn {obj_expr};"
        return self._request(
            "POST",
            "/eval",
            context="move_object",
            data=expr.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def recycle_object(self, object_curie: str) -> Any:
        target_expr = self._curie_to_moo_expr(object_curie)
        expr = f"recycle({target_expr});\nreturn 1;"
        return self._request(
            "POST",
            "/eval",
            context="recycle_object",
            data=expr.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )


