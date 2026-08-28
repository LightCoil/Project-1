
"""PROJECT-1 planner context and human-readable planner prompts."""

from typing import Any, Dict, List


def build_human_readable_prompt(
    task: str,
    available_models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> str:
    """Build the strategic planner request."""

    model_lines = []

    if available_models:
        for model in available_models:
            name = model.get("name", "unknown")
            provider = model.get("provider", "unknown")
            description = model.get("description", "")
            capabilities = model.get("capabilities", [])

            model_lines.append(
                f"- {name} "
                f"[{provider}] — "
                f"{description} — "
                f"capabilities: {', '.join(capabilities)}"
            )
    else:
        model_lines.append("- Нет доступных исполняемых моделей.")

    if history:
        history_lines = []

        for item in history:
            model = item.get("model", "unknown")
            subtask = item.get("task", "")
            result = item.get("result", "")

            history_lines.append(
                f"- {model}: {subtask}\n"
                f"  Результат: {result}"
            )

        existing = "\n".join(history_lines)
    else:
        existing = "Пока ничего не выполнено."

    if available_models:
        instruction = (
            "Распредели работу среди моделей. "
            "Используй только модели из списка доступных. "
            "Для каждой модели назначай конкретную небольшую "
            "подзадачу. Если дополнительная работа не требуется, "
            "скажи об этом."
        )
    else:
        instruction = (
            "Дополнительных моделей нет. "
            "Выполни необходимую работу сам."
        )

    return (
        "Доступны:\n"
        + "\n".join(model_lines)
        + "\n\n"
        + "Наша задача:\n"
        + task
        + "\n\n"
        + "Что уже есть:\n"
        + existing
        + "\n\n"
        + instruction
    )


def build_planner_context(
    task: str,
    available_models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build structured planner context."""

    return {
        "protocol_version": "2.5",
        "user_task": task,
        "available_models": list(available_models),
        "execution_history": list(history),
        "planner_instruction": (
            "Choose only executable models from available_models. "
            "Distribute small independent subtasks according to "
            "model capabilities. If there are no executable models, "
            "use ChatGPT-only mode."
        ),
    }
