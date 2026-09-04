
"""Planner context control for PROJECT-1 v2.3."""

from typing import Any, Dict, List


MAX_HISTORY_ITEMS = 12
MAX_RESULT_CHARS = 2500
MAX_TASK_CHARS = 1200
MAX_MODEL_DESCRIPTION_CHARS = 500


def _truncate(
    value: Any,
    limit: int,
) -> str:

    text = str(value or "")

    if len(text) <= limit:
        return text

    return text[:limit] + "\n[TRUNCATED]"


def compact_models(
    models: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    result = []

    for model in models or []:

        result.append({
            "name": str(
                model.get("name", "")
            ),
            "provider": str(
                model.get("provider", "")
            ),
            "description": _truncate(
                model.get(
                    "description",
                    ""
                ),
                MAX_MODEL_DESCRIPTION_CHARS,
            ),
            "capabilities": list(
                model.get(
                    "capabilities",
                    []
                ) or []
            ),
            "context_window": model.get(
                "context_window"
            ),
            "max_output_tokens": model.get(
                "max_output_tokens"
            ),
            "supports_streaming": bool(
                model.get(
                    "supports_streaming",
                    False
                )
            ),
            "supports_reasoning": bool(
                model.get(
                    "supports_reasoning",
                    False
                )
            ),
            "supports_code": bool(
                model.get(
                    "supports_code",
                    False
                )
            ),
            "availability": str(
                model.get(
                    "availability",
                    "unknown"
                )
            ),
        })

    return result


def compact_history(
    history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    history = list(history or [])

    if len(history) > MAX_HISTORY_ITEMS:
        history = history[
            -MAX_HISTORY_ITEMS:
        ]

    result = []

    for item in history:

        result.append({
            "model": _truncate(
                item.get(
                    "model",
                    ""
                ),
                200,
            ),
            "task": _truncate(
                item.get(
                    "task",
                    ""
                ),
                MAX_TASK_CHARS,
            ),
            "status": _truncate(
                item.get(
                    "status",
                    ""
                ),
                100,
            ),
            "result": _truncate(
                item.get(
                    "result",
                    ""
                ),
                MAX_RESULT_CHARS,
            ),
        })

    return result


def build_planner_context(
    user_task: str,
    available_models: List[Dict[str, Any]],
    execution_history: List[Dict[str, Any]],
) -> Dict[str, Any]:

    models = compact_models(
        available_models
    )

    history = compact_history(
        execution_history
    )

    if models:

        instruction = (
            "Доступны реальные модели. "
            "Распредели работу только между моделями "
            "из списка. "
            "Учитывай capabilities. "
            "Не назначай модели задачи, для которых "
            "они явно не предназначены. "
            "Если распределение излишне, скажи это. "
            "Если нужны дополнительные шаги, "
            "запроси их явно."
        )

    else:

        instruction = (
            "Доступных моделей нет. "
            "Распределение невозможно и не требуется. "
            "Работай самостоятельно как ChatGPT."
        )

    return {
        "protocol_version": "2.3",
        "user_task": _truncate(
            user_task,
            5000,
        ),
        "available_models": models,
        "execution_history": history,
        "planner_instruction": instruction,
    }


def build_human_readable_prompt(
    user_task: str,
    available_models: List[Dict[str, Any]],
    execution_history: List[Dict[str, Any]],
) -> str:

    context = build_planner_context(
        user_task,
        available_models,
        execution_history,
    )

    lines = []

    lines.append("Доступны:")

    models = context[
        "available_models"
    ]

    if models:

        for model in models:

            name = model["name"]
            provider = model["provider"]
            capabilities = ", ".join(
                model["capabilities"]
            )

            availability = model[
                "availability"
            ]

            lines.append(
                f"- {name} "
                f"[{provider}] "
                f"({availability}) — "
                f"{capabilities}"
            )

    else:

        lines.append("нет.")

    lines.append("")
    lines.append("Наша задача:")
    lines.append(
        context["user_task"]
    )

    lines.append("")
    lines.append("Что уже есть:")

    history = context[
        "execution_history"
    ]

    if history:

        for item in history:

            lines.append(
                f"- [{item['status']}] "
                f"{item['model']}: "
                f"{item['task']}"
            )

            lines.append(
                f"  Результат: "
                f"{item['result']}"
            )

    else:

        lines.append(
            "пока ничего."
        )

    lines.append("")

    lines.append(
        context["planner_instruction"]
    )

    if models:

        lines.append(
            "Если работа действительно нужна, "
            "распредели её между подходящими моделями."
        )

    else:

        lines.append(
            "Сформулируй необходимую работу "
            "и выполни её самостоятельно."
        )

    return "\n".join(lines)
