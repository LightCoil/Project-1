
from __future__ import annotations

import os
import traceback
from typing import Any

import gradio as gr

from research_engine.domain.worker import Worker, WorkerRole
from research_engine.domain.generation import GenerationRequest
from research_engine.engine.http_client import HttpGenerationClient
from research_engine.engine.model_config import ModelConfig, ModelRegistry
from research_engine.engine.worker_runtime import WorkerRuntime
from research_engine.engine.worker_executor import WorkerExecutor


# ================================================================
# CONFIG
# ================================================================

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 50


# ================================================================
# HELPERS
# ================================================================

def clean_api_url(api_url: str) -> str:
    """
    Normalize a user-supplied OpenAI-compatible API base URL.

    Accepted:
        https://host
        https://host/v1
        https://host/v1/chat/completions

    Returned form:
        https://host/v1
    """
    from urllib.parse import urlparse

    value = (api_url or "").strip().rstrip("/")

    if not value:
        return ""

    if value.endswith("/chat/completions"):
        value = value[:-len("/chat/completions")].rstrip("/")

    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            "API URL must start with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError(
            "API URL must contain a valid host."
        )

    if not value.endswith("/v1"):
        value += "/v1"

    return value

def extract_content(result: Any) -> str:
    """
    Extract generated text from the real Project-1
    WorkerExecutionResult without assuming a fake API.
    """

    # Most likely public attribute.
    for name in (
        "content",
        "text",
        "output",
        "generated_text",
        "response",
    ):
        if hasattr(result, name):
            value = getattr(result, name)
            if isinstance(value, str):
                return value

    # Some result objects may expose generation/result objects.
    for name in ("generation", "result"):
        if hasattr(result, name):
            nested = getattr(result, name)
            if isinstance(nested, str):
                return nested

            for attr in ("content", "text", "output", "generated_text"):
                if hasattr(nested, attr):
                    value = getattr(nested, attr)
                    if isinstance(value, str):
                        return value

    # Last-resort string representation.
    return str(result)


def make_runtime(
    *,
    api_url: str,
    api_key: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
):
    """
    Construct the real Project-1 execution chain.

    UI values are passed directly into the real runtime:

        API URL
            ↓
        ModelConfig.endpoint
            ↓
        HttpGenerationClient.endpoint

        API Key
            ↓
        HttpGenerationClient.api_key

        Model
            ↓
        ModelConfig.model
            ↓
        Worker.model
            ↓
        HTTP payload["model"]
    """

    endpoint = clean_api_url(api_url)

    if not endpoint:
        raise ValueError("API URL is required.")

    model_name = (model_name or "").strip()

    if not model_name:
        raise ValueError("Model is required.")

    model_config = ModelConfig(
        name="ui-gemma-model",
        provider="openai-compatible",
        model=model_name,
        endpoint=endpoint,
        max_tokens=int(max_tokens),
        temperature=float(temperature),
    )

    registry = ModelRegistry()
    registry.register(model_config)

    # IMPORTANT:
    # Worker.model is the actual provider model identifier.
    worker = Worker(
        id="ui-gemma-worker",
        name="Project-1 UI Worker",
        role=WorkerRole.GENERATOR,
        model=model_name,
        endpoint=endpoint,
        provider="openai-compatible",
    )

    client = HttpGenerationClient(
        endpoint=endpoint,
        api_key=(api_key or "").strip() or None,
        timeout=180,
    )

    runtime = WorkerRuntime(
        worker=worker,
        model_config=model_config,
        client=client,
        registry=registry,
    )

    executor = WorkerExecutor(
        runtime=runtime,
        client=client,
    )

    return worker, runtime, executor

def execute_stage(
    *,
    executor: WorkerExecutor,
    worker: Worker,
    runtime: WorkerRuntime,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    """
    Execute one real Project-1 generation.

    WorkerExecutor.execute() is called using its actual keyword-only API.
    """

    request = GenerationRequest(
        system_prompt="You are a philosophical research engine. Analyze the task rigorously and respond directly.",
        user_prompt=prompt,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )

    # The WorkerRuntime belongs to the execution path.
    # Depending on the current Worker implementation, runtime may already
    # be resolved by the executor through the worker/model registry.
    #
    # The important point is that execute() receives:
    #   worker=...
    #   request=...
    result = executor.execute(
        worker=worker,
        request=request,
    )

    return result


# ================================================================
# MODEL DISCOVERY
# ================================================================

def discover_models(api_url: str, api_key: str):
    import requests

    endpoint = clean_api_url(api_url)

    if not endpoint:
        return gr.update(choices=[], value=None), "❌ API URL is required."

    url = endpoint + "/models"

    headers = {}
    if (api_key or "").strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        models = []

        for item in data.get("data", []):
            if isinstance(item, dict) and item.get("id"):
                models.append(item["id"])

        if not models:
            return (
                gr.update(choices=[], value=None),
                "⚠️ API responded successfully, but no models were returned.",
            )

        return (
            gr.update(
                choices=models,
                value=models[0],
            ),
            f"✅ Discovered {len(models)} model(s).",
        )

    except Exception as exc:
        return (
            gr.update(choices=[], value=None),
            f"❌ Model discovery failed: {type(exc).__name__}: {exc}",
        )


# ================================================================
# PIPELINE
# ================================================================

def run_pipeline(
    api_url,
    api_key,
    model_name,
    thesis,
    temperature,
    max_tokens,
):
    empty = "Waiting for execution..."

    try:
        if not (api_url or "").strip():
            raise ValueError("API URL is required.")

        if not (model_name or "").strip():
            raise ValueError("Model is required.")

        if not (thesis or "").strip():
            raise ValueError("Thesis / Query is required.")

        temperature = float(temperature)
        max_tokens = int(max_tokens)

        if max_tokens < 1:
            raise ValueError("Max tokens must be >= 1.")

        worker, runtime, executor = make_runtime(
            api_url=api_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # --------------------------------------------------------
        # A
        # --------------------------------------------------------

        stage_a_prompt = f"""
You are Stage A of a philosophical research pipeline.

Analyze the following thesis rigorously.

THESIS:
{thesis}

Provide an initial philosophical analysis.
Identify the central concepts, assumptions, distinctions,
and the main structure of the problem.
""".strip()

        result_a = execute_stage(
            executor=executor,
            worker=worker,
            runtime=runtime,
            prompt=stage_a_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        a = extract_content(result_a)

        # --------------------------------------------------------
        # B
        # --------------------------------------------------------

        stage_b_prompt = f"""
You are Stage B, the critical stage of a philosophical research pipeline.

Critically examine Stage A.
Identify hidden assumptions, weaknesses, ambiguities,
unsupported claims, conceptual problems, and possible objections.

THESIS:
{thesis}

STAGE A:
{a}
""".strip()

        result_b = execute_stage(
            executor=executor,
            worker=worker,
            runtime=runtime,
            prompt=stage_b_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        b = extract_content(result_b)

        # --------------------------------------------------------
        # C
        # --------------------------------------------------------

        stage_c_prompt = f"""
You are Stage C, the counterargument stage.

Construct a serious counterargument to Stage B.
Do not merely repeat Stage A.
Challenge the critic where appropriate and develop
an alternative philosophical position.

THESIS:
{thesis}

STAGE A:
{a}

STAGE B:
{b}
""".strip()

        result_c = execute_stage(
            executor=executor,
            worker=worker,
            runtime=runtime,
            prompt=stage_c_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        c = extract_content(result_c)

        # --------------------------------------------------------
        # D
        # --------------------------------------------------------

        stage_d_prompt = f"""
You are Stage D, the second critical stage.

Critically examine the counterargument from Stage C.
Look for unsupported premises, logical gaps,
conceptual confusion, contradictions, and weaknesses.

THESIS:
{thesis}

STAGE B:
{b}

STAGE C:
{c}
""".strip()

        result_d = execute_stage(
            executor=executor,
            worker=worker,
            runtime=runtime,
            prompt=stage_d_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        d = extract_content(result_d)

        # --------------------------------------------------------
        # E
        # --------------------------------------------------------

        stage_e_prompt = f"""
You are Stage E, the final synthesis stage.

Produce a concise philosophical synthesis.
Integrate the strongest points from the entire A → D process.
Do not simply summarize the stages.
State the resulting position on the thesis and explain
the decisive considerations.

THESIS:
{thesis}

STAGE A:
{a}

STAGE B:
{b}

STAGE C:
{c}

STAGE D:
{d}
""".strip()

        result_e = execute_stage(
            executor=executor,
            worker=worker,
            runtime=runtime,
            prompt=stage_e_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        e = extract_content(result_e)

        status = (
            f"✅ Pipeline completed successfully\n"
            f"Model: {model_name}\n"
            f"Temperature: {temperature}\n"
            f"Max tokens / stage: {max_tokens}"
        )

        return a, b, c, d, e, status

    except Exception as exc:
        error = (
            f"❌ Pipeline failed\n\n"
            f"**{type(exc).__name__}:** `{exc}`"
        )

        print("\n" + "=" * 70)
        print("PROJECT-1 UI PIPELINE ERROR")
        print("=" * 70)
        traceback.print_exc()
        print("=" * 70)

        return empty, empty, empty, empty, empty, error


# ================================================================
# DARK UI
# ================================================================

CSS = r"""
:root {
    --bg: #0b0f14;
    --panel: #111820;
    --panel2: #151e28;
    --border: #273442;
    --text: #e7edf3;
    --muted: #9aa8b6;
}

body,
.gradio-container {
    background: var(--bg) !important;
    color: var(--text) !important;
}

.gradio-container {
    max-width: 1100px !important;
}

.block,
.form,
.panel,
.tabs,
.tabitem {
    background: var(--panel) !important;
    border-color: var(--border) !important;
}

textarea,
input,
select {
    background: #0d141c !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

label,
span,
p,
.prose {
    color: var(--text) !important;
}

button {
    border-color: var(--border) !important;
}

#title {
    text-align: center;
}

#title h1 {
    margin-bottom: 4px;
}

#subtitle {
    text-align: center;
    color: var(--muted) !important;
}

.result-box textarea {
    min-height: 190px !important;
}

.status-box {
    font-weight: 600;
}

footer {
    display: none !important;
}
"""


with gr.Blocks(
    title="Project-1 Research Engine",
    css=CSS,
    theme=gr.themes.Base(
        primary_hue="slate",
        neutral_hue="slate",
    ),
) as demo:

    gr.Markdown(
        "# 🧠 Project-1 Research Engine",
        elem_id="title",
    )

    gr.Markdown(
        "Minimal interface for the real Project-1 A → E philosophical pipeline.",
        elem_id="subtitle",
    )

    with gr.Accordion(
        "⚙️ Model API configuration",
        open=True,
    ):
        api_url = gr.Textbox(
            label="API URL",
            placeholder="https://xxxx.trycloudflare.com/v1",
        )

        api_key = gr.Textbox(
            label="API Key",
            type="password",
            placeholder="Optional",
        )

        with gr.Row():
            model_name = gr.Dropdown(
                label="Model",
                choices=[],
                allow_custom_value=True,
                value="",
            )

            discover_button = gr.Button(
                "🔍 Discover Models",
                variant="secondary",
            )

        discovery_status = gr.Markdown(
            "Enter API URL and API key, then click **Discover Models**."
        )

        with gr.Row():
            temperature = gr.Number(
                label="Temperature",
                value=DEFAULT_TEMPERATURE,
                minimum=0,
                maximum=2,
                step=0.05,
            )

            max_tokens = gr.Number(
                label="Max tokens / stage",
                value=DEFAULT_MAX_TOKENS,
                minimum=1,
                precision=0,
                step=1,
            )

    gr.Markdown("## 🔬 Research")

    thesis = gr.Textbox(
        label="Thesis / Query",
        placeholder="Enter a philosophical thesis or research question...",
        lines=4,
    )

    run_button = gr.Button(
        "🚀 Run A → E",
        variant="primary",
        size="lg",
    )

    status = gr.Markdown(
        "Ready.",
        elem_classes=["status-box"],
    )

    gr.Markdown("## Results")

    stage_a = gr.Textbox(
        label="🧠 Stage A — Initial Analysis",
        value="Waiting for execution...",
        lines=10,
        elem_classes=["result-box"],
    )

    stage_b = gr.Textbox(
        label="🔎 Stage B — Critic",
        value="Waiting for execution...",
        lines=10,
        elem_classes=["result-box"],
    )

    stage_c = gr.Textbox(
        label="⚔️ Stage C — Counterargument",
        value="Waiting for execution...",
        lines=10,
        elem_classes=["result-box"],
    )

    stage_d = gr.Textbox(
        label="🔬 Stage D — Second Critic",
        value="Waiting for execution...",
        lines=10,
        elem_classes=["result-box"],
    )

    stage_e = gr.Textbox(
        label="🎯 Stage E — Final Synthesis",
        value="Waiting for execution...",
        lines=10,
        elem_classes=["result-box"],
    )

    # ------------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------------

    discover_button.click(
        fn=discover_models,
        inputs=[api_url, api_key],
        outputs=[model_name, discovery_status],
    )

    # IMPORTANT:
    # Pipeline is NOT executed during interface initialization.
    # It only runs after the user explicitly presses the button.
    run_button.click(
        fn=run_pipeline,
        inputs=[
            api_url,
            api_key,
            model_name,
            thesis,
            temperature,
            max_tokens,
        ],
        outputs=[
            stage_a,
            stage_b,
            stage_c,
            stage_d,
            stage_e,
            status,
        ],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=False,
    )
