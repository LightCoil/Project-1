
"""PROJECT-1 ChatGPT planner adapter v2.6.

The adapter deliberately does not perform network requests.
It defines the boundary between the orchestrator and ChatGPT.

A real transport can later implement:
    ChatGPTPlannerAdapter.complete(prompt)

without changing orchestration logic.
"""

from typing import Any, Callable, Dict, Optional
import json


class ChatGPTPlannerAdapter:
    """Adapter boundary for a ChatGPT strategic planner."""

    def __init__(
        self,
        transport: Optional[Callable[[str], Any]] = None,
    ):
        self.transport = transport
        self.calls = []

    # ------------------------------------------------------------
    # PUBLIC PLANNER INTERFACE
    # ------------------------------------------------------------

    def __call__(self, prompt: str) -> Dict[str, Any]:
        return self.plan(prompt)

    def plan(self, prompt: str) -> Dict[str, Any]:
        """Send planner prompt through the configured transport."""

        self.calls.append(prompt)

        if self.transport is None:
            return self.development_response(prompt)

        raw = self.transport(prompt)

        return self.normalize_response(raw)

    # ------------------------------------------------------------
    # TRANSPORT BOUNDARY
    # ------------------------------------------------------------

    def complete(self, prompt: str) -> Any:
        """Explicit transport method.

        This is intentionally unavailable until a real
        ChatGPT transport is connected.
        """

        if self.transport is None:
            raise RuntimeError(
                "ChatGPT transport is not configured."
            )

        return self.transport(prompt)

    # ------------------------------------------------------------
    # RESPONSE NORMALIZATION
    # ------------------------------------------------------------

    @staticmethod
    def normalize_response(
        raw: Any,
    ) -> Dict[str, Any]:

        if isinstance(raw, dict):
            data = dict(raw)

        elif isinstance(raw, str):

            text = raw.strip()

            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "ChatGPT planner returned non-JSON "
                    "response."
                ) from exc

        else:
            raise TypeError(
                "Unsupported ChatGPT planner response type."
            )

        if not isinstance(data, dict):
            raise ValueError(
                "ChatGPT planner response must be an object."
            )

        mode = data.get("mode")

        if mode not in {
            "distributed",
            "chatgpt_only",
        }:
            raise ValueError(
                "Planner decision must use mode "
                "'distributed' or 'chatgpt_only'."
            )

        assignments = data.get(
            "assignments",
            [],
        )

        if not isinstance(assignments, list):
            raise ValueError(
                "Planner assignments must be a list."
            )

        normalized = []

        for item in assignments:

            if not isinstance(item, dict):
                raise ValueError(
                    "Each assignment must be an object."
                )

            model = item.get("model")
            task = item.get("task")

            if not model or not task:
                raise ValueError(
                    "Each assignment requires "
                    "model and task."
                )

            normalized.append(
                {
                    "model": str(model),
                    "task": str(task),
                }
            )

        return {
            "mode": mode,
            "assignments": normalized,
            "reason": str(
                data.get(
                    "reason",
                    "",
                )
            ),
            "final_instruction": str(
                data.get(
                    "final_instruction",
                    "",
                )
            ),
        }

    # ------------------------------------------------------------
    # DEVELOPMENT MODE
    # ------------------------------------------------------------

    @staticmethod
    def development_response(
        prompt: str,
    ) -> Dict[str, Any]:

        if "Распредели работу" in prompt:

            return {
                "mode": "distributed",
                "assignments": [
                    {
                        "model": "local_reasoning",
                        "task": (
                            "Провести независимый "
                            "анализ задачи."
                        ),
                    }
                ],
                "reason": (
                    "В development mode задача "
                    "передана подходящей локальной модели."
                ),
                "final_instruction": (
                    "После получения результата "
                    "оценить его достаточность."
                ),
            }

        return {
            "mode": "chatgpt_only",
            "assignments": [],
            "reason": (
                "Дополнительная работа "
                "не требуется."
            ),
            "final_instruction": (
                "Выполнить задачу самостоятельно."
            ),
        }
