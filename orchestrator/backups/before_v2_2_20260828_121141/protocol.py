
"""PROJECT-1 Orchestrator command protocol."""

from dataclasses import dataclass, field
from typing import Any


COMMANDS = {
    "ASK_MODEL": {
        "description": "Assign a task to a model.",
        "required": ["model", "task"],
    },
    "ASK_GPT": {
        "description": "Ask the strategic planner for another decision.",
        "required": ["prompt"],
    },
    "REVIEW_RESULTS": {
        "description": "Review accumulated model results.",
        "required": [],
    },
    "FINISH": {
        "description": "Finish orchestration.",
        "required": [],
    },
}


@dataclass
class Command:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in COMMANDS:
            raise ValueError(f"Unknown command: {self.type}")

        for key in COMMANDS[self.type]["required"]:
            if key not in self.payload:
                raise ValueError(
                    f"Command {self.type} requires field: {key}"
                )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "type": self.type,
            "payload": self.payload,
        }


def parse_command(data: dict[str, Any]) -> Command:
    command = Command(
        type=str(data.get("type", "")).strip(),
        payload=dict(data.get("payload", {})),
    )
    command.validate()
    return command
