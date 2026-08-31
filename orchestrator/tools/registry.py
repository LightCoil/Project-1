
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

    ToolRegistry owns the tool contract boundary.

    The model may request a tool, but every invocation passes
    through schema validation before execution.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    # ================================================================
    # REGISTRATION
    # ================================================================

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

    # ================================================================
    # LOOKUP
    # ================================================================

    def get(self, name: str) -> ToolDefinition:

        if name not in self._tools:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    # ================================================================
    # CONTRACT VALIDATION
    # ================================================================

    def validate_arguments(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate tool arguments against input_schema.

        V1 supports:
          - object arguments;
          - required fields;
          - declared properties;
          - primitive string/number/integer/boolean types;
          - additionalProperties=False.

        The original dictionary is not modified.
        """

        definition = self.get(name)
        schema = definition.input_schema or {}

        if not isinstance(arguments, dict):
            raise TypeError(
                f"Arguments for '{name}' must be a dictionary."
            )

        if schema.get("type") != "object":
            return dict(arguments)

        properties = schema.get(
            "properties",
            {},
        )

        required = schema.get(
            "required",
            [],
        )

        # ------------------------------------------------------------
        # Required fields
        # ------------------------------------------------------------

        for field in required:
            if field not in arguments:
                raise ValueError(
                    f"Missing required argument "
                    f"'{field}' for tool '{name}'."
                )

        # ------------------------------------------------------------
        # Unknown fields
        # ------------------------------------------------------------

        if schema.get(
            "additionalProperties",
            True,
        ) is False:

            unknown = sorted(
                set(arguments)
                - set(properties)
            )

            if unknown:
                raise ValueError(
                    f"Unknown argument(s) for tool "
                    f"'{name}': {unknown}"
                )

        # ------------------------------------------------------------
        # Primitive type checking
        # ------------------------------------------------------------

        for field, value in arguments.items():

            if field not in properties:
                continue

            field_schema = properties[field]
            expected = field_schema.get("type")

            if expected == "string":
                valid = isinstance(value, str)

            elif expected == "integer":
                valid = (
                    isinstance(value, int)
                    and not isinstance(value, bool)
                )

            elif expected == "number":
                valid = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                )

            elif expected == "boolean":
                valid = isinstance(value, bool)

            elif expected == "object":
                valid = isinstance(value, dict)

            elif expected == "array":
                valid = isinstance(value, list)

            else:
                valid = True

            if not valid:
                raise TypeError(
                    f"Argument '{field}' for tool "
                    f"'{name}' must be of type "
                    f"'{expected}'."
                )

        return dict(arguments)

    # ================================================================
    # EXECUTION
    # ================================================================

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:

        validated = self.validate_arguments(
            name,
            arguments,
        )

        definition = self.get(name)

        return definition.implementation.execute(
            validated
        )

    # ================================================================
    # MODEL DESCRIPTION
    # ================================================================

    def schemas(self) -> list[dict[str, Any]]:

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    # ================================================================
    # DEBUGGING
    # ================================================================

    def names(self) -> list[str]:
        return list(self._tools.keys())
