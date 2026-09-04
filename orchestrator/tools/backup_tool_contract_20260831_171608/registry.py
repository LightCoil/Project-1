
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    """
    Metadata describing a tool available to the Agent.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    implementation: Any


class ToolRegistry:
    """
    Central registry for Agent tools.

    The Agent does not need to know where a tool comes from.
    It only knows its name and schema.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    # ------------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------------

    def register(self, tool: Any) -> None:

        name = getattr(tool, "name", None)

        if not name:
            raise ValueError(
                "Tool must define a 'name'."
            )

        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        definition = ToolDefinition(
            name=name,
            description=getattr(
                tool,
                "description",
                "",
            ),
            input_schema=getattr(
                tool,
                "input_schema",
                {},
            ),
            implementation=tool,
        )

        self._tools[name] = definition

    # ------------------------------------------------------------
    # LOOKUP
    # ------------------------------------------------------------

    def get(self, name: str) -> ToolDefinition:

        if name not in self._tools:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    # ------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:

        definition = self.get(name)

        return definition.implementation.execute(
            arguments
        )

    # ------------------------------------------------------------
    # MODEL DESCRIPTION
    # ------------------------------------------------------------

    def schemas(self) -> list[dict[str, Any]]:

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    # ------------------------------------------------------------
    # DEBUGGING
    # ------------------------------------------------------------

    def names(self) -> list[str]:
        return list(self._tools.keys())
