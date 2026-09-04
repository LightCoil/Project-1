
"""Planner context construction for PROJECT-1 v2.2."""

from typing import Any, Dict, List


def build_planner_context(
    user_task: str,
    available_models: List[Dict[str, Any]],
    execution_history: List[Dict[str, Any]],
) -> Dict[str, Any]:

    models = list(available_models or [])
    history = list(execution_history or [])

    if models:
        planner_instruction = (
            "Доступны модели. "
            "Распредели работу только между реально доступными моделями. "
            "Не придумывай отсутствующие модели. "
            "Если дополнительная работа не нужна, заверши задачу. "
            "Если часть задачи лучше выполнить тебе самому, "
            "можешь выбрать режим chatgpt_only для этой части."
        )
    else:
        planner_instruction = (
            "Дополнительных моделей нет. "
            "Распределять работу не требуется. "
            "Выполни необходимую интеллектуальную работу самостоятельно "
            "или укажи следующий необходимый шаг."
        )

    return {
        "protocol_version": "2.2",
        "user_task": user_task,
        "available_models": models,
        "execution_history": history,
        "planner_instruction": planner_instruction,
    }


def build_human_readable_prompt(
    user_task: str,
    available_models: List[Dict[str, Any]],
    execution_history: List[Dict[str, Any]],
) -> str:
    """
    Build the exact strategic-advisor message.

    The advisor is explicitly told whether model distribution
    is meaningful.
    """

    models = list(available_models or [])
    history = list(execution_history or [])

    lines = []

    lines.append("Доступны:")

    if models:
        for model in models:
            name = model.get("name", "unknown")
            provider = model.get("provider", "unknown")
            capabilities = ", ".join(
                model.get("capabilities", [])
            )

            lines.append(
                f"- {name} [{provider}] — {capabilities}"
            )
    else:
        lines.append("нет.")

    lines.append("")
    lines.append("Наша задача:")
    lines.append(user_task.strip())

    lines.append("")
    lines.append("Что уже есть:")

    if history:
        for item in history:
            model = item.get("model", "unknown")
            task = item.get("task", "")
            result = item.get("result", "")

            lines.append(f"- Модель: {model}")
            lines.append(f"  Задание: {task}")
            lines.append(f"  Результат: {result}")
    else:
        lines.append("пока ничего.")

    lines.append("")

    if models:
        lines.append(
            "Распредели работу среди моделей. "
            "Если считаешь, что это излишне, то скажи сейчас."
        )
    else:
        lines.append(
            "Дополнительных моделей нет. "
            "Распределять работу не требуется. "
            "Определи, что нужно сделать, и выполни эту работу сам."
        )

    return "\n".join(lines)
