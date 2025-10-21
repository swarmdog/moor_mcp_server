from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PromptDefinition:
    name: str
    description: str
    text: str

    def as_metadata(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}


class PromptRegistry:
    def __init__(self) -> None:
        self._prompts: Dict[str, PromptDefinition] = {}
        self._register(
            PromptDefinition(
                name="create-room",
                description="Guide for creating a simple room object and setting its description.",
                text=(
                    "1. Call the `create_object` tool with parent `sysobj:room` and owner `player`.\n"
                    "2. Use `set_property` to set the `name` and `description` fields.\n"
                    "3. Confirm success via `get_property`."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="update-verb",
                description="Steps to ensure and update a verb's source code.",
                text=(
                    "1. Call `ensure_verb` with the target object and verb name.\n"
                    "2. Invoke `program_verb` with the full verb source (no inline comments).\n"
                    "3. Optionally run `invoke_verb` to smoke-test the change."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="inspect-player",
                description="Inspect a player's verbs and properties.",
                text=(
                    "1. Resolve the player with `resolve_object` (e.g., match(\"Name\")).\n"
                    "2. Call `list_properties` and `list_verbs` with `inherited=true`.\n"
                    "3. Fetch specific data with `get_property` or `get_verb`."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="build-scene-bundle",
                description="Create a region, scene, and supporting zone or actor objects for a new location.",
                text=(
                    "1. Create each container (region, scene, zones, hazards, NPCs) with `create_object`, matching the parent prototype such as `sysobj:room` or `sysobj:thing`.\n"
                    "2. Populate naming, descriptions, and tag arrays using repeated `set_property` calls so the new pieces slot into navigation and encounter logic.\n"
                    "3. Move hazards or NPCs beneath the scene root via `move_object` and verify relationships with `list_properties`."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="wire-scene-exits",
                description="Add bi-directional exits between scenes or zones and confirm travel verbs work.",
                text=(
                    "1. Resolve both endpoints with `resolve_object` to capture their oid:* identifiers.\n"
                    "2. Create or update exit objects using `create_object` (or `set_property` on existing exits) so each exit's `dest` points at the opposite room.\n"
                    "3. Smoke-test traversal with `invoke_verb` (e.g., the exit's movement verb) and watch for navigation updates via `list_presentations`."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="stage-scene-ui",
                description="Trigger scene automation and manage the resulting player-facing presentations.",
                text=(
                    "1. Use `invoke_verb` on the scene controller or PC object to fire abilities that call `present(...)`.\n"
                    "2. Fetch the active notifications with `list_presentations` and review their metadata before sharing with the player.\n"
                    "3. Dismiss stale cards via `dismiss_presentation` once validation is complete so the UI stays clean."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="relocate-object",
                description="Safely move objects (props, NPCs, hazards) into their new homes.",
                text=(
                    "1. Resolve the source object and target container with `resolve_object`.\n"
                    "2. Call `move_object` and confirm the result includes the canonical oid for the new parent.\n"
                    "3. Double-check placement with `get_property` or `list_properties` on the destination, and undo by moving back if validation fails."
                ),
            )
        )
        self._register(
            PromptDefinition(
                name="retire-object",
                description="Recycle obsolete prototypes or clutter safely.",
                text=(
                    "1. Resolve the object slated for removal and ensure it is not the active location for any players.\n"
                    "2. Move it into a staging container (or straight to the recycler) with `move_object` if necessary.\n"
                    "3. Call `recycle_object` and capture the confirmation for audit logs via `get_history`."
                ),
            )
        )

    def _register(self, definition: PromptDefinition) -> None:
        self._prompts[definition.name] = definition

    def list_prompts(self) -> List[Dict[str, str]]:
        return [definition.as_metadata() for definition in self._prompts.values()]

    def get_prompt(self, name: str) -> PromptDefinition:
        if name not in self._prompts:
            raise KeyError(name)
        return self._prompts[name]
