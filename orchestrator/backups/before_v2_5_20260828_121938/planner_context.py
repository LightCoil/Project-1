
"""PROJECT-1 Orchestrator planner context v2.4."""

from typing import Any, Dict, List


def _model_name(model: Any) -> str:
    if isinstance(model, dict):
        return str(
            model.get("name")
            or model.get("model")
            or ""
        )

    return str(
        getattr(model, "name", "")
        or getattr(model, "model", "")
        or ""
    )


def _model_description(model: Any) -> str:
    if isinstance(model, dict):
        return str(
            model.get("description")
            or ""
        )

    return str(
        getattr(model, "description", "")
        or ""
    )


def _model_capabilities(model: Any) -> List[str]:
    if isinstance(model, dict):
        value = model.get("capabilities") or []
    else:
        value = (
            getattr(model, "capabilities", None)
            or []
        )

    if isinstance(value, str):
        return [value]

    return [str(x) for x in value]


def normalize_model_description(
    model: Any,
) -> Dict[str, Any]:
    return {
        "name": _model_name(model),
        "description": _model_description(model),
        "capabilities": _model_capabilities(model),
    }


def build_planner_context(
    task: str,
    available_models: List[Any],
    history: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:

    history = list(history or [])

    return {
        "protocol_version": "2.4",
        "user_task": str(task),
        "available_models": [
            normalize_model_description(model)
            for model in available_models
        ],
        "execution_history": history,
    }


def build_human_readable_prompt(
    task: str,
    available_models: List[Any],
    history: List[Dict[str, Any]] | None = None,
) -> str:

    history = list(history or [])

    # ------------------------------------------------------------
    # ZERO MODEL MODE
    # ------------------------------------------------------------

    if not available_models:

        return (
            "Ты — стратегический исполнитель задачи.\n\n"
            "Доступных внешних или локальных моделей сейчас нет.\n\n"
            "Наша задача:\n"
            f"{task}\n\n"
            "Что уже есть:\n"
            f"{history if history else 'Пока ничего нет.'}\n\n"
            "Дополнительных моделей нет. "
            "Распределять работу не нужно.\n"
            "Выполни необходимую интеллектуальную работу сам.\n"
            "Дай максимально полезный следующий результат."
        )

    # ------------------------------------------------------------
    # MODEL DISTRIBUTION MODE
    # ------------------------------------------------------------

    lines = [
        "Ты — стратегический планировщик PROJECT-1.",
        "",
        "Доступны:",
    ]

    for model in available_models:
        info = normalize_model_description(model)

        name = info["name"] or "unnamed_model"
        description = info["description"]
        capabilities = ", ".join(
            info["capabilities"]
        )

        lines.append(f"- {name}")

        if description:
            lines.append(
                f"  Описание: {description}"
            )

        if capabilities:
            lines.append(
                f"  Возможности: {capabilities}"
            )

    lines.extend([
        "",
        "Наша задача:",
        str(task),
        "",
        "Что уже есть:",
        (
            str(history)
            if history
            else "Пока ничего нет."
        ),
        "",
        "Распредели работу среди моделей.",
        "",
        "Правила:",
        "1. Используй только модели из списка выше.",
        "2. Назначай задачи с учётом их возможностей.",
        "3. Не создавай несуществующие модели.",
        "4. Не поручай моделям работу, которую они явно "
        "не способны выполнять.",
        "5. Если дополнительная работа не нужна, "
        "скажи об этом явно.",
        "6. Если уже достаточно результатов для ответа, "
        "не создавай лишних заданий.",
        "",
        "Верни структурированное решение.",
    ])

    return "\n".join(lines)
