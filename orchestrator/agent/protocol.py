
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ================================================================
# ACTION TYPES
# ================================================================

class ActionType(str, Enum):

    TOOL_CALL = "tool_call"
    FINISH = "finish"


# ================================================================
# OBSERVATION TYPES
# ================================================================

class ObservationType(str, Enum):

    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"


# ================================================================
# TOOL CALL
# ================================================================

@dataclass(frozen=True)
class ToolCall:

    tool: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self):

        if not self.tool:
            raise ValueError(
                "ToolCall.tool cannot be empty."
            )


# ================================================================
# ACTION
# ================================================================

@dataclass(frozen=True)
class Action:

    type: ActionType

    tool_call: ToolCall | None = None

    message: str | None = None

    @classmethod
    def tool(
        cls,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> "Action":

        return cls(
            type=ActionType.TOOL_CALL,
            tool_call=ToolCall(
                tool=name,
                arguments=arguments or {},
            ),
        )

    @classmethod
    def finish(
        cls,
        message: str,
    ) -> "Action":

        return cls(
            type=ActionType.FINISH,
            message=message,
        )


# ================================================================
# OBSERVATION
# ================================================================

@dataclass(frozen=True)
class Observation:

    type: ObservationType

    success: bool

    content: str

    tool: str | None = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def success_result(
        cls,
        tool: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Observation":

        return cls(
            type=ObservationType.TOOL_RESULT,
            success=True,
            content=content,
            tool=tool,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        tool: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Observation":

        return cls(
            type=ObservationType.TOOL_ERROR,
            success=False,
            content="",
            tool=tool,
            error=error,
            metadata=metadata or {},
        )


# ================================================================
# AGENT EVENT
# ================================================================

@dataclass(frozen=True)
class AgentEvent:

    type: str

    data: dict[str, Any] = field(
        default_factory=dict
    )
