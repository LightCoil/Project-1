
"""PROJECT-1 planner context v2.5."""

import json
from typing import Any, Dict, List


def build_v25_planner_prompt(
    task: str,
    available_models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
    previous_answer: str = "",
) -> str:

    models_text = json.dumps(
        available_models,
        ensure_ascii=False,
        indent=2,
    )

    history_text = json.dumps(
        history[-12:],
        ensure_ascii=False,
        indent=2,
    )

    if not history:
        history_text = "Нет выполненной работы."

    if not previous_answer:
        previous_answer = "Нет."

    return f"""
Ты являешься стратегическим планировщиком PROJECT-1.

Доступны:
{models_text}

Наша задача:
{task}

Что уже есть:
{history_text}

Предыдущий ответ/результат ChatGPT:
{previous_answer}

Твоя задача — определить следующий минимальный полезный шаг.

Если доступны модели, распредели работу только среди реально
доступных моделей.

Если моделей нет, НЕ пытайся распределять работу.
В этом случае режим должен быть chatgpt_only, а необходимую
работу следует выполнить через ChatGPT.

Не выдумывай модели.
Не создавай работу ради самой работы.
Если информации уже достаточно, выбери finish.
Если требуется проверка существующего результата, выбери review.
Если требуется дополнительная работа локальных моделей,
выбери assignments.

Верни только JSON следующего вида:

{{
  "mode": "assignments | chatgpt_only | review | finish",
  "assignments": [
    {{
      "model": "точное имя модели из списка",
      "task": "конкретная небольшая задача",
      "expected_output": "что должна вернуть модель",
      "priority": "normal"
    }}
  ],
  "chatgpt_task": "задача для ChatGPT, если она нужна",
  "review_task": "задача проверки, если нужна",
  "final_answer": "финальный ответ, если работа уже завершена",
  "rationale": "краткое объяснение решения"
}}

Задания должны быть небольшими и проверяемыми.
""".strip()


def build_planner_context(
    task: str,
    available_models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
):
    return {
        "protocol_version": "2.5",
        "user_task": task,
        "available_models": available_models,
        "history": history[-12:],
    }


def build_human_readable_prompt(
    task: str,
    available_models: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
):
    return build_v25_planner_prompt(
        task,
        available_models,
        history,
    )
