
from orchestrator.agent_runtime import (
    Action,
    AgentState,
    AgentTask,
    Tool,
    ToolRegistry,
    ToolResult,
    AgentLoop,
)


def test_tool_registry():

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="echo",
            description="Return the supplied value",
            schema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string"
                    }
                },
                "required": ["value"],
            },
            execute=lambda value: ToolResult.ok(
                value
            ),
        )
    )

    assert registry.has("echo")
    assert "echo" in registry.list_tools()

    result = registry.execute(
        "echo",
        {"value": "hello"},
    )

    assert result.success
    assert result.output == "hello"


def test_agent_loop():

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="echo",
            description="Return supplied value",
            schema={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string"
                    }
                },
            },
            execute=lambda value: ToolResult.ok(
                value
            ),
        )
    )

    calls = []

    def model_step(task, history, tools):

        calls.append(len(history))

        if len(history) == 0:
            return Action(
                tool="echo",
                arguments={
                    "value": "PROJECT-1"
                },
            )

        return Action(
            completion="DONE"
        )

    task = AgentTask(
        id="test-001",
        prompt="Test agent loop",
    )

    agent = AgentLoop(
        model_step=model_step,
        tools=registry,
        max_steps=8,
    )

    result = agent.run(task)

    assert result.state == AgentState.COMPLETED
    assert result.result == "DONE"

    assert len(result.observations) == 1
    assert (
        result.observations[0].result.output
        == "PROJECT-1"
    )

    assert calls == [0, 1]


def test_tool_error_becomes_observation():

    registry = ToolRegistry()

    def broken_tool():
        raise RuntimeError("intentional failure")

    registry.register(
        Tool(
            name="broken",
            description="Always fails",
            schema={
                "type": "object"
            },
            execute=broken_tool,
        )
    )

    calls = []

    def model_step(task, history, tools):

        calls.append(len(history))

        if len(history) == 0:
            return Action(
                tool="broken"
            )

        return Action(
            completion="RECOVERED"
        )

    task = AgentTask(
        id="test-error",
        prompt="Test recovery observation",
    )

    agent = AgentLoop(
        model_step=model_step,
        tools=registry,
        max_steps=8,
    )

    result = agent.run(task)

    assert result.state == AgentState.COMPLETED
    assert result.result == "RECOVERED"

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.result.success is False
    assert "intentional failure" in (
        observation.result.error
    )
