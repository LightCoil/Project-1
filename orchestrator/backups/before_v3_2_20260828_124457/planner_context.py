
"""PROJECT-1 planner context v3.1."""

import json
from typing import Any, Dict, List


def _model_lines(models: List[Dict[str, Any]]) -> str:
    if not models:
        return "Дополнительных моделей нет."

    lines = []

    for model in models:
        name = model.get("name", "unknown")
        provider = model.get("provider", "unknown")
        description = model.get("description", "")
        capabilities = model.get("capabilities", [])

        lines.append(
            f"- {name} [{provider}]"
        )

        if description:
            lines.append(
                f"  Назначение: {description}"
            )

        if capabilities:
            lines.append(
                "  Возможности: "
                + ", ".join(str(x) for x in capabilities)
            )

    return "\n".join(lines)


def _history_text(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "Пока ничего не выполнено."

    blocks = []

    for index, item in enumerate(history, 1):
        model = item.get("model", "unknown")
        task = item.get("task", "")
        result = item.get("result", "")

        blocks.append(
            f"[Результат {index}]\n"
            f"Модель: {model}\n"
            f"Задание: {task}\n"
            f"Результат:\n{result}"
        )

    return "\n\n".join(blocks)


def build_human_readable_prompt(
    task: str,
    models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> str:

    return (
        "Доступны:\n"
        + _model_lines(models)
        + "\n\n"
        "Наша задача:\n"
        + task
        + "\n\n"
        "Что уже есть:\n"
        + _history_text(history)
        + "\n\n"
        "Распредели работу среди моделей.\n"
        "Если дополнительных моделей нет, выполни необходимую работу сам.\n"
        "Не выбирай модели, которых нет в списке.\n"
        "Назначай только небольшие, конкретные и проверяемые задачи.\n"
        "Если имеющихся результатов уже достаточно, сообщи, что работа завершена.\n"
        "Если нужен следующий этап, сформулируй его явно."
    )


def build_review_prompt(
    task: str,
    models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> str:

    return (
        "Доступны:\n"
        + _model_lines(models)
        + "\n\n"
        "Наша задача:\n"
        + task
        + "\n\n"
        "Что уже есть:\n"
        + _history_text(history)
        + "\n\n"
        "Проведи критическую проверку полученных результатов.\n"
        "Определи, достаточно ли материала для завершения задачи.\n"
        "Если недостаточно — назначь следующий небольшой этап.\n"
        "Если достаточно — сообщи FINISH.\n"
        "Используй только модели из списка."
    )


def build_zero_model_prompt(
    task: str,
    history: List[Dict[str, Any]],
) -> str:

    return (
        "Дополнительных моделей нет.\n\n"
        "Наша задача:\n"
        + task
        + "\n\n"
        "Что уже есть:\n"
        + _history_text(history)
        + "\n\n"
        "Выполни необходимую работу сам.\n"
        "Если задача уже выполнена, сообщи FINISH."
    )
