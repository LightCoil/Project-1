
from __future__ import annotations

from typing import Any, Callable

from .protocol import (
    Action,
    ActionType,
    AgentEvent,
    Observation,
)

from orchestrator.tools.registry import ToolRegistry


class AgentRuntime:
    """
    PROJECT-1 Agent Runtime v0.2

    Strict execution loop:

        Model
          ↓
        Action
          ↓
        ToolRegistry
          ↓
        Observation
          ↓
        Model
          ↓
        ...

    The runtime owns execution state.

    The model owns decision making.

    Tools own external actions.
    """

    def __init__(
        self,
        model: Callable[
            [list[dict[str, Any]]],
            Any,
        ],
        tools: ToolRegistry | None = None,
        max_steps: int = 20,
        event_handler: Callable[
            [AgentEvent],
            None,
        ] | None = None,
    ):

        self.model = model

        self.tool_registry = (
            tools
            if tools is not None
            else ToolRegistry()
        )

        self.max_steps = max_steps

        self.event_handler = (
            event_handler
        )

        self.history: list[
            dict[str, Any]
        ] = []

        self.step_count = 0

        self.last_action: Action | None = None

        self.last_observation: (
            Observation | None
        ) = None

    # ============================================================
    # EVENTS
    # ============================================================

    def emit(
        self,
        event_type: str,
        **data: Any,
    ) -> None:

        event = AgentEvent(
            type=event_type,
            data=data,
        )

        if self.event_handler:
            self.event_handler(event)

    # ============================================================
    # MODEL → ACTION
    # ============================================================

    def parse_action(
        self,
        raw: Any,
    ) -> Action:

        # Already normalized.
        if isinstance(
            raw,
            Action,
        ):
            return raw

        # --------------------------------------------------------
        # Dictionary representation
        # --------------------------------------------------------

        if isinstance(
            raw,
            dict,
        ):

            action_type = raw.get(
                "type"
            )

            # TOOL CALL
            if action_type == "tool_call":

                tool_call = raw.get(
                    "tool_call"
                )

                if not isinstance(
                    tool_call,
                    dict,
                ):
                    raise ValueError(
                        "tool_call must be a dictionary."
                    )

                tool_name = tool_call.get(
                    "tool"
                )

                if not tool_name:
                    raise ValueError(
                        "tool_call.tool is required."
                    )

                arguments = tool_call.get(
                    "arguments",
                    {},
                )

                if not isinstance(
                    arguments,
                    dict,
                ):
                    raise ValueError(
                        "tool_call.arguments must be a dictionary."
                    )

                return Action.tool(
                    name=tool_name,
                    arguments=arguments,
                )

            # FINISH
            if action_type == "finish":

                return Action.finish(
                    message=str(
                        raw.get(
                            "message",
                            "",
                        )
                    )
                )

            raise ValueError(
                f"Unknown action type: {action_type}"
            )

        # --------------------------------------------------------
        # Unsupported model output
        # --------------------------------------------------------

        raise TypeError(
            "Model returned unsupported "
            f"action type: {type(raw).__name__}"
        )

    # ============================================================
    # TOOL EXECUTION
    # ============================================================

    def execute_tool(
        self,
        action: Action,
    ) -> Observation:

        if action.type != ActionType.TOOL_CALL:
            raise ValueError(
                "execute_tool requires TOOL_CALL."
            )

        if action.tool_call is None:
            raise ValueError(
                "TOOL_CALL contains no ToolCall."
            )

        tool_name = action.tool_call.tool

        arguments = (
            action.tool_call.arguments
        )

        self.emit(
            "tool.before",
            tool=tool_name,
            arguments=arguments,
        )

        # --------------------------------------------------------
        # Unknown tool
        # --------------------------------------------------------

        if not self.tool_registry.has(
            tool_name
        ):

            observation = Observation.failure(
                tool=tool_name,
                error=(
                    f"Unknown tool: {tool_name}"
                ),
            )

            self.emit(
                "tool.after",
                tool=tool_name,
                success=False,
                error=observation.error,
            )

            return observation

        # --------------------------------------------------------
        # Execute
        # --------------------------------------------------------

        try:

            result = (
                self.tool_registry.execute(
                    tool_name,
                    arguments,
                )
            )

            observation = (
                Observation.success_result(
                    tool=tool_name,
                    content=str(result),
                )
            )

            self.emit(
                "tool.after",
                tool=tool_name,
                success=True,
                result=str(result),
            )

            return observation

        except Exception as exc:

            observation = Observation.failure(
                tool=tool_name,
                error=str(exc),
            )

            self.emit(
                "tool.after",
                tool=tool_name,
                success=False,
                error=str(exc),
            )

            return observation

    # ============================================================
    # HISTORY
    # ============================================================

    def record_action(
        self,
        action: Action,
    ) -> None:

        self.history.append({
            "role": "assistant",
            "action": action,
        })

    def record_observation(
        self,
        observation: Observation,
    ) -> None:

        self.history.append({
            "role": "tool",
            "observation": observation,
        })

    # ============================================================
    # SINGLE STEP
    # ============================================================

    def step(self) -> Action:

        self.emit(
            "model.before",
            history=self.history,
        )

        raw = self.model(
            self.history
        )

        self.emit(
            "model.after",
            response=raw,
        )

        action = self.parse_action(
            raw
        )

        self.last_action = action

        self.record_action(
            action
        )

        return action

    # ============================================================
    # MAIN LOOP
    # ============================================================

    def run(
        self,
        task: str,
    ) -> dict[str, Any]:

        self.history = []

        self.step_count = 0

        self.last_action = None

        self.last_observation = None

        # --------------------------------------------------------
        # Initial user task
        # --------------------------------------------------------

        self.history.append({
            "role": "user",
            "content": task,
        })

        self.emit(
            "agent.start",
            task=task,
        )

        # --------------------------------------------------------
        # LOOP
        # --------------------------------------------------------

        while (
            self.step_count
            < self.max_steps
        ):

            self.emit(
                "agent.step",
                step=self.step_count,
            )

            try:

                action = self.step()

            except Exception as exc:

                self.emit(
                    "agent.error",
                    step=self.step_count,
                    error=str(exc),
                )

                return {
                    "status": "failed",
                    "reason": "invalid_action",
                    "error": str(exc),
                    "steps": self.step_count,
                    "history": self.history,
                }

            # ----------------------------------------------------
            # FINISH
            # ----------------------------------------------------

            if (
                action.type
                == ActionType.FINISH
            ):

                message = (
                    action.message
                    or ""
                )

                self.emit(
                    "agent.complete",
                    message=message,
                    steps=self.step_count + 1,
                )

                return {
                    "status": "completed",
                    "message": message,
                    "steps": (
                        self.step_count + 1
                    ),
                    "history": self.history,
                }

            # ----------------------------------------------------
            # TOOL CALL
            # ----------------------------------------------------

            observation = (
                self.execute_tool(
                    action
                )
            )

            self.last_observation = (
                observation
            )

            self.record_observation(
                observation
            )

            self.step_count += 1

        # --------------------------------------------------------
        # MAX STEPS
        # --------------------------------------------------------

        self.emit(
            "agent.failed",
            reason="max_steps",
            steps=self.step_count,
        )

        return {
            "status": "failed",
            "reason": "max_steps",
            "steps": self.step_count,
            "history": self.history,
        }
