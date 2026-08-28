import json

"""
PROJECT-1 Chat Bridge v3.4

Transport boundary between the orchestrator and the ChatGPT
conversation interface.

IMPORTANT:
This module does NOT use the OpenAI API.
It does NOT contain an API key.
It does NOT automate or scrape a ChatGPT session.

The bridge intentionally exposes a transport-neutral interface:

    orchestrator -> build_request()
    user/chat -> ChatGPT
    ChatGPT -> response
    user -> submit_response()
    bridge -> orchestrator

A future transport can replace this class without changing the
orchestration protocol.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str


@dataclass
class ChatExchange:
    request: ChatMessage
    response: Optional[ChatMessage] = None


class ChatGPTChatBridge:

    transport = "chat_manual"

    def __init__(self):
        self.history = []

    def build_request(
        self,
        task: str,
        available_models=None,
        execution_history=None,
        phase: str = "planning",
    ) -> str:

        available_models = list(available_models or [])
        execution_history = list(execution_history or [])

        lines = []

        lines.append(
            "Ты выступаешь как стратегический планировщик "
            "оркестратора PROJECT-1."
        )

        lines.append("")
        lines.append("Доступны:")

        if available_models:
            for model in available_models:
                name = model.get("name", "unknown")
                provider = model.get("provider", "unknown")
                capabilities = ", ".join(
                    model.get("capabilities", [])
                )

                lines.append(
                    f"- {name} | provider={provider} "
                    f"| capabilities={capabilities}"
                )
        else:
            lines.append("- дополнительных моделей нет")

        lines.append("")
        lines.append("Наша задача:")
        lines.append(task)

        lines.append("")
        lines.append("Что уже есть:")

        if execution_history:
            for item in execution_history:
                model = item.get("model", "unknown")
                assigned = item.get("task", "")
                result = item.get("result", "")

                lines.append(
                    f"- Модель: {model}"
                )
                lines.append(
                    f"  Задание: {assigned}"
                )
                lines.append(
                    f"  Результат: {result}"
                )
        else:
            lines.append("- Пока ничего не выполнено.")

        lines.append("")
        lines.append(f"Текущая фаза: {phase}")

        if available_models:
            lines.append("")
            lines.append(
                "Распредели работу среди доступных моделей."
            )
            lines.append(
                "Давай только небольшие, конкретные задания."
            )
            lines.append(
                "Используй только модели из списка."
            )
            lines.append(
                "Если дополнительная работа не нужна, "
                "верни FINISH."
            )
        else:
            lines.append("")
            lines.append(
                "Дополнительных моделей нет. "
                "Выполни необходимую работу сам."
            )

        lines.append("")
        lines.append(
            "Верни ответ в формате JSON."
        )
        lines.append(
            "Не добавляй Markdown до или после JSON."
        )

        if available_models:
            lines.append(
                """
{
  "action": "ASSIGN" или "FINISH",
  "assignments": [
    {
      "model": "точное имя модели",
      "task": "маленькое конкретное задание"
    }
  ],
  "final_instruction": "если FINISH — итоговая инструкция/синтез"
}
""".strip()
            )
        else:
            lines.append(
                """
{
  "action": "FINISH",
  "assignments": [],
  "final_instruction": "ответ на исходную задачу"
}
""".strip()
            )

        return "\n".join(lines)

    def create_exchange(
        self,
        task: str,
        available_models=None,
        execution_history=None,
        phase: str = "planning",
    ) -> ChatExchange:

        request = self.build_request(
            task=task,
            available_models=available_models,
            execution_history=execution_history,
            phase=phase,
        )

        message = ChatMessage(
            role="user",
            content=request,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        exchange = ChatExchange(
            request=message
        )

        self.history.append(exchange)

        return exchange

    def submit_response(
        self,
        exchange: ChatExchange,
        response: str,
    ):

        if not isinstance(response, str):
            raise TypeError(
                "ChatGPT response must be a string."
            )

        response = response.strip()

        if not response:
            raise ValueError(
                "ChatGPT response is empty."
            )

        exchange.response = ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        return response

    def parse_json_response(
        self,
        response: str,
    ) -> Dict[str, Any]:

        response = response.strip()

        # Remove accidental fenced JSON.
        if response.startswith("```"):
            lines = response.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            response = "\n".join(lines).strip()

        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"ChatGPT returned invalid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "ChatGPT response must be a JSON object."
            )

        action = data.get("action")

        if action not in {
            "ASSIGN",
            "FINISH",
        }:
            raise ValueError(
                "ChatGPT decision must contain "
                "action=ASSIGN or action=FINISH."
            )

        assignments = data.get(
            "assignments",
            [],
        )

        if not isinstance(assignments, list):
            raise ValueError(
                "assignments must be a list."
            )

        for assignment in assignments:

            if not isinstance(
                assignment,
                dict,
            ):
                raise ValueError(
                    "Every assignment must be an object."
                )

            if action == "ASSIGN":

                if not assignment.get("model"):
                    raise ValueError(
                        "Assignment is missing model."
                    )

                if not assignment.get("task"):
                    raise ValueError(
                        "Assignment is missing task."
                    )

        if action == "FINISH":
            assignments = []

        data["assignments"] = assignments

        return data


# Explicit alias used by future transports.
ChatGPTPlannerTransport = ChatGPTChatBridge
