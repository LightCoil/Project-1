
"""
PROJECT-1 Agent Runtime
=======================

Chapter I / 1.1.1

Core loop:

    Task
      ↓
    Model
      ↓
    Action
      ↓
    Tool
      ↓
    Observation
      ↓
    Model
      ↓
    ...

The runtime deliberately knows nothing about a specific LLM.

The model layer is injected through `model_step`.

This keeps Agent Runtime independent from:
    - Qwen
    - Gemma
    - OpenAI-compatible APIs
    - TextGen
    - ExLlama
    - future models

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time
import traceback


# ================================================================
# TASK STATE
# ================================================================

class AgentState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


# ================================================================
# ACTION
# ================================================================

@dataclass
class Action:
    """
    A model-requested action.

    Example:

        Action(
            tool="read_file",
            arguments={"path": "foo.py"}
        )

    Completion:

        Action(
            tool=None,
            arguments={},
            completion="Task completed"
        )
    """

    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)

    completion: Optional[str] = None

    def is_completion(self) -> bool:
        return self.tool is None


# ================================================================
# TOOL RESULT
# ================================================================

@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        output: Any = None,
        **metadata: Any,
    ) -> "ToolResult":
        return cls(
            success=True,
            output=output,
            metadata=metadata,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        **metadata: Any,
    ) -> "ToolResult":
        return cls(
            success=False,
            error=error,
            metadata=metadata,
        )


# ================================================================
# OBSERVATION
# ================================================================

@dataclass
class Observation:
    """
    What the agent observes after an action.
    """

    action: Action
    result: ToolResult

    step: int

    timestamp: float = field(
        default_factory=time.time
    )


# ================================================================
# TOOL
# ================================================================

@dataclass
class Tool:
    name: str
    description: str
    schema: Dict[str, Any]
    execute: Callable[..., ToolResult]


# ================================================================
# TOOL REGISTRY
# ================================================================

class ToolRegistry:
    """
    Central registry for agent tools.

    This becomes the foundation for:

        filesystem
        terminal
        browser
        MCP
        skills
        plugins
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> ToolResult:

        tool = self.get(name)

        try:
            result = tool.execute(arguments)

            if isinstance(result, ToolResult):
                return result

            return ToolResult.ok(result)

        except Exception as exc:
            return ToolResult.fail(
                error=str(exc),
                exception_type=type(exc).__name__,
                traceback=traceback.format_exc(),
            )


# ================================================================
# TASK
# ================================================================

@dataclass
class AgentTask:
    id: str
    prompt: str

    state: AgentState = AgentState.PENDING

    step: int = 0

    observations: List[Observation] = field(
        default_factory=list
    )

    result: Optional[str] = None
    error: Optional[str] = None


# ================================================================
# AGENT LOOP
# ================================================================

class AgentLoop:
    """
    PROJECT-1 Agent Runtime.

    The model is deliberately injected:

        model_step(task, history, tools) -> Action

    Therefore AgentLoop does not care which model is being used.
    """

    def __init__(
        self,
        model_step: Callable[
            [AgentTask, List[Observation], List[Dict[str, Any]]],
            Action,
        ],
        tools: ToolRegistry,
        max_steps: int = 32,
    ) -> None:

        self.model_step = model_step
        self.tools = tools
        self.max_steps = max_steps

    def run(self, task: AgentTask) -> AgentTask:

        if task.state != AgentState.PENDING:
            raise ValueError(
                f"Task must start in PENDING state, "
                f"got {task.state}"
            )

        task.state = AgentState.RUNNING

        while task.step < self.max_steps:

            task.step += 1

            # ------------------------------------------------
            # MODEL
            # ------------------------------------------------

            try:
                action = self.model_step(
                    task,
                    task.observations,
                    self.tools.schemas(),
                )

            except Exception as exc:

                task.state = AgentState.FAILED
                task.error = (
                    f"Model error: {exc}"
                )

                return task

            if not isinstance(action, Action):

                task.state = AgentState.FAILED
                task.error = (
                    "Model returned invalid action: "
                    f"{type(action).__name__}"
                )

                return task

            # ------------------------------------------------
            # COMPLETION
            # ------------------------------------------------

            if action.is_completion():

                task.state = AgentState.COMPLETED
                task.result = action.completion

                return task

            # ------------------------------------------------
            # TOOL
            # ------------------------------------------------

            task.state = AgentState.WAITING

            observation_result = self.tools.execute(
                action.tool,
                action.arguments,
            )

            observation = Observation(
                action=action,
                result=observation_result,
                step=task.step,
            )

            task.observations.append(
                observation
            )

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            if not observation_result.success:

                task.state = AgentState.RECOVERING

                # Important:
                # We DO NOT terminate immediately.
                #
                # The model receives the failed observation
                # and gets another chance to reason.
                #
                # Recovery Engine will become a separate
                # component in Chapter II.

                continue

            task.state = AgentState.RUNNING

        # ----------------------------------------------------
        # STEP LIMIT
        # ----------------------------------------------------

        task.state = AgentState.FAILED

        task.error = (
            f"Maximum agent steps exceeded: "
            f"{self.max_steps}"
        )

        return task


# ================================================================
# SIMPLE FACTORY
# ================================================================

def create_runtime(
    model_step: Callable,
    tools: ToolRegistry,
    max_steps: int = 32,
) -> AgentLoop:

    return AgentLoop(
        model_step=model_step,
        tools=tools,
        max_steps=max_steps,
    )
