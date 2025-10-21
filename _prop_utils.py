"""Utilities for working with property payloads returned by the mooR REST API."""

from __future__ import annotations

from typing import Any, Optional


def extract_obj_curie(payload: Any) -> Optional[str]:
    """Extract an object CURIE from a property payload.

    The `/properties/{object}/{name}` endpoint returns a JSON object with metadata about the
    property and a ``value`` key containing the serialized MOO value.  For object references the
    value is encoded as ``{"obj": "oid:123"}``.  Some test doubles and older mocks provided the
    shorthand form where the top-level payload already had an ``obj`` key.  This helper normalizes
    both shapes and returns the CURIE when present.
    """

    if not isinstance(payload, dict):
        return None

    obj = payload.get("obj")
    if isinstance(obj, str):
        return obj

    value = payload.get("value")
    if isinstance(value, dict):
        obj_value = value.get("obj")
        if isinstance(obj_value, str):
            return obj_value

    return None
