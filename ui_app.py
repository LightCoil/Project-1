
from __future__ import annotations
import re

import os
import traceback
from typing import Any

import gradio as gr


# ================================================================
# PROJECT-1 — FINAL SYNTHESIS MAIN UI
# ================================================================


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



# ====================================================================
# PROJECT-1 — ROBUST A-E STORAGE VALIDATOR v1
# ====================================================================

def _validate_cycle_ae_document(text: str) -> bool:
    """
    Validate the structural A→E storage contract.

    Important:
    Generated model text is arbitrary and may use its own headings.
    Validation therefore relies only on the canonical storage headers.
    """
    if not isinstance(text, str):
        return False

    required_headers = [
        "STAGE A",
        "STAGE B",
        "STAGE C",
        "STAGE D",
        "STAGE E",
    ]

    positions = []

    for header in required_headers:
        marker = f"\n{header}\n"
        pos = text.find(marker)

        if pos == -1:
            # Also permit the first header at byte zero.
            if text.startswith(f"{header}\n"):
                pos = 0
            else:
                return False

        positions.append(pos)

    # Canonical headers must occur in A→E order.
    return positions == sorted(positions)


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

def _discover_models_impl(api_url: str, api_key: str):
    """
    Discover models from an OpenAI-compatible API.

    Primary endpoint:
        GET <endpoint>/v1/models

    Fallback endpoints are supported for compatibility with
    simple/local model servers.

    Returns:
        tuple[list[str], str]
    """

    import requests

    if not api_url or not str(api_url).strip():
        raise ValueError("API URL is required.")

    endpoint = str(api_url).strip().rstrip("/")

    # --------------------------------------------------------------
    # Authentication
    # --------------------------------------------------------------

    headers = {
        "Accept": "application/json",
    }

    if api_key and str(api_key).strip():
        headers["Authorization"] = (
            f"Bearer {str(api_key).strip()}"
        )

    # --------------------------------------------------------------
    # Candidate discovery endpoints
    # --------------------------------------------------------------

    candidates = []

    if endpoint.endswith("/v1/models"):
        candidates.append(endpoint)

    elif endpoint.endswith("/v1"):
        candidates.append(
            f"{endpoint}/models"
        )

    else:
        candidates.extend([
            f"{endpoint}/v1/models",
            f"{endpoint}/models",
        ])

    # Remove duplicates while preserving order.
    candidates = list(dict.fromkeys(candidates))

    last_error = None

    # --------------------------------------------------------------
    # Query provider
    # --------------------------------------------------------------

    for models_url in candidates:

        try:
            response = requests.get(
                models_url,
                headers=headers,
                timeout=15,
            )

            # A 404 means this endpoint is not supported.
            if response.status_code == 404:
                last_error = (
                    f"{models_url}: HTTP 404"
                )
                continue

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as exc:
                last_error = (
                    f"{models_url}: invalid JSON response"
                )
                continue

            # ------------------------------------------------------
            # OpenAI-compatible format:
            #
            # {
            #   "data": [
            #       {"id": "model-name", ...}
            #   ]
            # }
            # ------------------------------------------------------

            models = []

            if isinstance(data, dict):

                raw_models = data.get("data")

                if isinstance(raw_models, list):
                    for item in raw_models:

                        if isinstance(item, dict):
                            model_id = (
                                item.get("id")
                                or item.get("name")
                                or item.get("model")
                            )

                            if model_id:
                                models.append(
                                    str(model_id)
                                )

                        elif isinstance(item, str):
                            models.append(item)

                # --------------------------------------------------
                # Simple API formats
                # --------------------------------------------------

                if not models:
                    raw_models = data.get("models")

                    if isinstance(raw_models, list):
                        for item in raw_models:

                            if isinstance(item, dict):
                                model_id = (
                                    item.get("id")
                                    or item.get("name")
                                    or item.get("model")
                                )

                                if model_id:
                                    models.append(
                                        str(model_id)
                                    )

                            elif isinstance(item, str):
                                models.append(item)

                # --------------------------------------------------
                # Single-model response
                # --------------------------------------------------

                if not models:
                    model_id = (
                        data.get("model")
                        or data.get("model_name")
                        or data.get("id")
                        or data.get("name")
                    )

                    if model_id:
                        models.append(
                            str(model_id)
                        )

            # ------------------------------------------------------
            # Direct list response
            # ------------------------------------------------------

            elif isinstance(data, list):

                for item in data:

                    if isinstance(item, dict):
                        model_id = (
                            item.get("id")
                            or item.get("name")
                            or item.get("model")
                        )

                        if model_id:
                            models.append(
                                str(model_id)
                            )

                    elif isinstance(item, str):
                        models.append(item)

            # ------------------------------------------------------
            # Normalize
            # ------------------------------------------------------

            normalized = []

            for model in models:

                model = str(model).strip()

                if model and model not in normalized:
                    normalized.append(model)

            if normalized:

                status = (
                    f"🟢 Discovered "
                    f"{len(normalized)} model(s)."
                )

                return (
                    normalized,
                    status,
                )

            last_error = (
                f"{models_url}: API returned no model IDs"
            )

        except requests.RequestException as exc:

            last_error = (
                f"{models_url}: "
                f"{type(exc).__name__}: {exc}"
            )

    # --------------------------------------------------------------
    # No model discovered
    # --------------------------------------------------------------

    if last_error:
        raise RuntimeError(
            "Model discovery failed. "
            f"Last attempt: {last_error}"
        )

    raise RuntimeError(
        "Model discovery failed: "
        "no compatible model endpoint found."
    )


# ================================================================
# PROJECT-1 — DISCOVER MODELS OUTPUT NORMALIZER
# ================================================================

def discover_models(api_url, api_key):
    """
    Compatibility wrapper for the Gradio Discover Models event.

    Gradio expects exactly two outputs:
        1. model dropdown value/update
        2. discovery status

    The original implementation is preserved as
    _discover_models_impl().
    """

    try:
        result = _discover_models_impl(
            api_url,
            api_key,
        )

        # Already correct.
        if isinstance(result, tuple):
            if len(result) == 2:
                return result

            if len(result) == 1:
                return (
                    result[0],
                    "🟢 Models discovered.",
                )

            return (
                None,
                "⚠️ Model discovery returned an unexpected result.",
            )

        # Original implementation returned None.
        if result is None:
            return (
                None,
                "⚠️ No models were returned by the API.",
            )

        # Original implementation returned only the model value.
        return (
            result,
            "🟢 Models discovered.",
        )

    except Exception as exc:
        print("\n" + "=" * 70)
        print("PROJECT-1 MODEL DISCOVERY ERROR")
        print("=" * 70)

        import traceback
        traceback.print_exc()

        print("=" * 70)

        return (
            None,
            f"❌ Model discovery failed: "
            f"{type(exc).__name__}: {exc}",
        )


import os
import json
from datetime import datetime



# ================================================================
# PROJECT-1 — DOCUMENT SYSTEM
# ================================================================

PROJECT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "project_data",
)

DOCUMENTS_DIR = os.path.join(
    PROJECT_DATA_DIR,
    "documents",
)

PROJECT_METADATA_FILE = os.path.join(
    PROJECT_DATA_DIR,
    "project.json",
)


def ensure_document_storage():
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

    if not os.path.exists(PROJECT_METADATA_FILE):
        metadata = {
            "project": "Project-1",
            "version": 1,
            "documents": [],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        with open(
            PROJECT_METADATA_FILE,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2,
            )


def load_project_metadata():
    ensure_document_storage()

    try:
        with open(
            PROJECT_METADATA_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = {}

    data.setdefault("project", "Project-1")
    data.setdefault("version", 1)
    data.setdefault("documents", [])

    return data


def update_project_metadata():
    ensure_document_storage()

    metadata = load_project_metadata()

    documents = []

    for filename in sorted(os.listdir(DOCUMENTS_DIR)):
        if not filename.endswith(".txt"):
            continue

        path = os.path.join(DOCUMENTS_DIR, filename)

        if not os.path.isfile(path):
            continue

        stat = os.stat(path)

        documents.append(
            {
                "name": filename,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat(),
            }
        )

    metadata["documents"] = documents
    metadata["updated_at"] = datetime.utcnow().isoformat() + "Z"

    with open(
        PROJECT_METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return metadata


def list_documents():
    ensure_document_storage()

    update_project_metadata()

    return [
        filename
        for filename in sorted(os.listdir(DOCUMENTS_DIR))
        if filename.endswith(".txt")
        and os.path.isfile(
            os.path.join(DOCUMENTS_DIR, filename)
        )
    ]


def _safe_document_name(name):
    name = (name or "").strip()

    if not name:
        raise ValueError("Document name is required.")

    name = os.path.basename(name)

    if not name.endswith(".txt"):
        name += ".txt"

    if name in (".txt", "..txt"):
        raise ValueError("Invalid document name.")

    return name


def load_document(name):
    filename = _safe_document_name(name)

    path = os.path.join(
        DOCUMENTS_DIR,
        filename,
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Document not found: {filename}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def save_document(name, content):
    filename = _safe_document_name(name)

    ensure_document_storage()

    path = os.path.join(
        DOCUMENTS_DIR,
        filename,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(content or "")

    update_project_metadata()

    return filename


def create_document(name):
    filename = _safe_document_name(name)

    ensure_document_storage()

    path = os.path.join(
        DOCUMENTS_DIR,
        filename,
    )

    if os.path.exists(path):
        raise FileExistsError(
            f"Document already exists: {filename}"
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write("")

    update_project_metadata()

    return filename


def delete_document(name):
    filename = _safe_document_name(name)

    path = os.path.join(
        DOCUMENTS_DIR,
        filename,
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Document not found: {filename}"
        )

    os.remove(path)

    update_project_metadata()

    return list_documents()


def save_stage_document(stage_name, content):
    stage_name = str(stage_name).strip()

    if not stage_name:
        raise ValueError("Stage name is required.")

    filename = f"{stage_name}.txt"

    return save_document(
        filename,
        content or "",
    )


def save_all_stages(a, b, c, d, e):
    """
    Persist the complete A→E project document.

    Storage model:
        stage_a.txt
        stage_b.txt
        stage_c.txt
        stage_d.txt
        stage_e.txt
        A-E.txt

    The individual stage files preserve independent stage editing,
    while A-E.txt provides one loadable combined document.
    """
    ensure_document_storage()

    stages = {
        "stage_a": a or "",
        "stage_b": b or "",
        "stage_c": c or "",
        "stage_d": d or "",
        "stage_e": e or "",
    }

    saved = []

    # Save individual stages.
    for stage_name, content in stages.items():
        saved.append(
            save_stage_document(
                stage_name,
                content,
            )
        )

    # Build the canonical combined A→E document.
    combined_parts = []

    for stage_name, content in stages.items():
        letter = stage_name[-1].upper()

        combined_parts.append(
            f"## Stage {letter}\n\n"
            f"{content}\n"
        )

    combined_content = "\n".join(combined_parts).rstrip() + "\n"

    combined_filename = save_document(
        "A-E.txt",
        combined_content,
    )

    saved.append(combined_filename)

    update_project_metadata()

    return saved



# ================================================================
# PIPELINE
# ================================================================



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


def _run_pipeline_streaming_core(
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

        yield (
            a,
            "",
            "",
            "",
            "",
            "🟢 Stage A completed",
        )

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

        yield (
            a,
            b,
            "",
            "",
            "",
            "🟢 Stage B completed",
        )

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

        yield (
            a,
            b,
            c,
            "",
            "",
            "🟢 Stage C completed",
        )

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

        yield (
            a,
            b,
            c,
            d,
            "",
            "🟢 Stage D completed",
        )

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

        yield (
            a,
            b,
            c,
            d,
            e,
            "🟢 Stage E completed",
        )

        status = (
            f"✅ Pipeline completed successfully\n"
            f"Model: {model_name}\n"
            f"Temperature: {temperature}\n"
            f"Max tokens / stage: {max_tokens}"
        )

        yield (
            a,
            b,
            c,
            d,
            e,
            status,
        )

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

        yield (
            empty,
            empty,
            empty,
            empty,
            empty,
            error,
        )


# ================================================================
# PROJECT-1 A→E AUTOMATIC DOCUMENT PERSISTENCE
# ================================================================

def run_pipeline_streaming(
    api_url,
    api_key,
    model_name,
    thesis,
    temperature,
    max_tokens,
):
    """
    Public streaming adapter.

    Delegates generation to the original streaming implementation
    and automatically persists the completed A→E result.

    The Gradio output contract remains:
        (stage_a, stage_b, stage_c, stage_d, stage_e, status)
    """

    latest_result = None

    for result in _run_pipeline_streaming_core(
        api_url,
        api_key,
        model_name,
        thesis,
        temperature,
        max_tokens,
    ):
        latest_result = result
        yield result

    # ------------------------------------------------------------
    # Automatic persistence happens ONLY after the generator
    # completes successfully.
    # ------------------------------------------------------------

    try:
        if (
            isinstance(latest_result, tuple)
            and len(latest_result) >= 5
        ):
            stage_a = latest_result[0]
            stage_b = latest_result[1]
            stage_c = latest_result[2]
            stage_d = latest_result[3]
            stage_e = latest_result[4]

            save_all_stages(
                stage_a or "",
                stage_b or "",
                stage_c or "",
                stage_d or "",
                stage_e or "",
            )

            print("=" * 70)
            print("🟢 PROJECT-1 A→E AUTO-SAVE")
            print("=" * 70)
            print("🟢 Stage A saved")
            print("🟢 Stage B saved")
            print("🟢 Stage C saved")
            print("🟢 Stage D saved")
            print("🟢 Stage E saved")
            print("🟢 A-E.txt saved")
            print("=" * 70)

    except Exception as exc:
        # Generation itself must never be converted into a failure
        # solely because document persistence failed.
        print("=" * 70)
        print("⚠️ PROJECT-1 DOCUMENT AUTO-SAVE ERROR")
        print("=" * 70)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 70)


# ================================================================


# ================================================================
# PROJECT-1 CYCLE STORAGE v1
# ================================================================

CYCLE_STORAGE_DIR = os.path.join(
    DOCUMENTS_DIR,
    "runs",
)

FINAL_SYNTHESIS_DOCUMENT = "final_synthesis.txt"


def ensure_cycle_storage():
    """
    Ensure the cycle storage directory exists.
    """
    ensure_document_storage()
    os.makedirs(
        CYCLE_STORAGE_DIR,
        exist_ok=True,
    )


def _cycle_id(cycle_number):
    """
    Return canonical cycle identifier.

    Examples:
        1  -> run_001
        12 -> run_012
    """
    cycle_number = int(cycle_number)

    if cycle_number < 1:
        raise ValueError("Cycle number must be >= 1.")

    return f"run_{cycle_number:03d}"


def cycle_directory(cycle_number):
    """
    Return the storage directory for a cycle.
    """
    ensure_cycle_storage()

    return os.path.join(
        CYCLE_STORAGE_DIR,
        _cycle_id(cycle_number),
    )


def save_cycle_stages(
    cycle_number,
    a,
    b,
    c,
    d,
    e,
):
    """
    Save all five A→E stages inside one cycle directory.

    Existing global stage storage remains untouched.
    """

    cycle_dir = cycle_directory(cycle_number)

    os.makedirs(
        cycle_dir,
        exist_ok=True,
    )

    stages = {
        "stage_a.txt": a or "",
        "stage_b.txt": b or "",
        "stage_c.txt": c or "",
        "stage_d.txt": d or "",
        "stage_e.txt": e or "",
    }

    for filename, content in stages.items():
        path = os.path.join(
            cycle_dir,
            filename,
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(content)

    combined = (
        "================================================================\n"
        f"PROJECT-1 — CYCLE {int(cycle_number)}\n"
        "================================================================\n\n"
        "STAGE A\n"
        "----------------------------------------------------------------\n"
        f"{a or ''}\n\n"
        "STAGE B\n"
        "----------------------------------------------------------------\n"
        f"{b or ''}\n\n"
        "STAGE C\n"
        "----------------------------------------------------------------\n"
        f"{c or ''}\n\n"
        "STAGE D\n"
        "----------------------------------------------------------------\n"
        f"{d or ''}\n\n"
        "STAGE E\n"
        "----------------------------------------------------------------\n"
        f"{e or ''}\n"
    )

    combined_path = os.path.join(
        cycle_dir,
        "A-E.txt",
    )

    with open(
        combined_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(combined)

    return [
        os.path.join(_cycle_id(cycle_number), name)
        for name in [
            "stage_a.txt",
            "stage_b.txt",
            "stage_c.txt",
            "stage_d.txt",
            "stage_e.txt",
            "A-E.txt",
        ]
    ]


def load_cycle_document(cycle_number, name):
    """
    Load a document belonging to a specific cycle.
    """

    cycle_dir = cycle_directory(cycle_number)

    filename = _safe_document_name(name)

    path = os.path.join(
        cycle_dir,
        filename,
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Cycle document not found: {filename}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


def list_cycles():
    """
    Return existing cycle numbers in ascending order.
    """

    ensure_cycle_storage()

    result = []

    for name in os.listdir(CYCLE_STORAGE_DIR):

        match = re.fullmatch(
            r"run_(\d+)",
            name,
        )

        if not match:
            continue

        path = os.path.join(
            CYCLE_STORAGE_DIR,
            name,
        )

        if os.path.isdir(path):
            result.append(
                int(match.group(1))
            )

    return sorted(result)


def next_cycle_number():
    """
    Return the next available cycle number.

    First cycle is 1.
    """

    cycles = list_cycles()

    if not cycles:
        return 1

    return max(cycles) + 1


def append_final_synthesis(
    cycle_number,
    final_result,
    thesis="",
    model_name="",
    temperature=None,
    max_tokens=None,
):
    """
    Append Stage E from a cycle to the cumulative
    final_synthesis.txt document.

    Previous cycles are never overwritten.
    """

    ensure_cycle_storage()

    final_path = os.path.join(
        DOCUMENTS_DIR,
        FINAL_SYNTHESIS_DOCUMENT,
    )

    header = (
        "\n"
        "================================================================\n"
        f"PROJECT-1 — CYCLE {int(cycle_number)}\n"
        "================================================================\n\n"
        f"Date: {datetime.now().isoformat(timespec='seconds')}\n"
    )

    if model_name:
        header += f"Model: {model_name}\n"

    if temperature is not None:
        header += f"Temperature: {temperature}\n"

    if max_tokens is not None:
        header += f"Max tokens / stage: {max_tokens}\n"

    if thesis:
        header += (
            "\n"
            "THESIS:\n"
            "----------------------------------------------------------------\n"
            f"{thesis.strip()}\n"
        )

    header += (
        "\n"
        "STAGE E — FINAL SYNTHESIS\n"
        "----------------------------------------------------------------\n"
    )

    block = (
        header
        + f"{final_result or ''}\n"
    )

    with open(
        final_path,
        "a",
        encoding="utf-8",
    ) as f:
        f.write(block)

    return FINAL_SYNTHESIS_DOCUMENT


def load_final_synthesis():
    """
    Load the complete cumulative Stage E history.
    """

    ensure_document_storage()

    path = os.path.join(
        DOCUMENTS_DIR,
        FINAL_SYNTHESIS_DOCUMENT,
    )

    if not os.path.exists(path):
        return ""

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()


# ================================================================
# END PROJECT-1 CYCLE STORAGE v1
# ================================================================





# ================================================================
# PROJECT-1 MULTI-CYCLE ORCHESTRATION v1
# ================================================================

MULTI_CYCLE_STOP_REQUESTED = False


def request_multi_cycle_stop():
    """
    Request a graceful stop after the currently running cycle.

    The current cycle is allowed to finish and persist.
    No already completed cycle is deleted.
    """
    global MULTI_CYCLE_STOP_REQUESTED
    MULTI_CYCLE_STOP_REQUESTED = True
    return "🛑 Stop requested. Current cycle will finish safely."


def reset_multi_cycle_stop():
    """
    Clear a previous stop request before starting a new run.
    """
    global MULTI_CYCLE_STOP_REQUESTED
    MULTI_CYCLE_STOP_REQUESTED = False


def _normalize_cycle_count(cycle_count):
    """
    Convert the UI value into a safe cycle count.

    Supported values:
        positive integer -> exact number of cycles
        0 / None         -> invalid
    """
    try:
        cycle_count = int(cycle_count)
    except (TypeError, ValueError):
        raise ValueError("Number of cycles must be an integer.")

    if cycle_count < 1:
        raise ValueError("Number of cycles must be >= 1.")

    return cycle_count


def _extract_streaming_result(item):
    """
    Normalize one streaming yield.

    The existing public streaming generator returns:

        (stage_a, stage_b, stage_c, stage_d, stage_e, status)

    This helper intentionally does not alter the underlying generator.
    """
    if not isinstance(item, (tuple, list)):
        raise RuntimeError(
            "run_pipeline_streaming() returned an unexpected value."
        )

    if len(item) != 6:
        raise RuntimeError(
            "run_pipeline_streaming() must yield exactly six values."
        )

    return tuple(item)


def run_multi_cycle_streaming(
    api_url,
    api_key,
    model_name,
    thesis,
    temperature,
    max_tokens,
    cycle_count,
):
    # PROJECT-1: hard safety limit — 25 tokens per stage
    max_tokens = 25
    """
    Execute the existing A→E streaming pipeline repeatedly.

    Each cycle:
        A → B → C → D → E
            ↓
        cycle storage
            ↓
        final_synthesis.txt

    The E result of the previous cycle becomes the context for the
    next cycle.

    The original run_pipeline_streaming() remains untouched.
    """

    reset_multi_cycle_stop()

    cycle_count = _normalize_cycle_count(cycle_count)

    current_thesis = (thesis or "").strip()

    if not current_thesis:
        raise ValueError("Thesis / Query is required.")

    for cycle_index in range(1, cycle_count + 1):

        if MULTI_CYCLE_STOP_REQUESTED:
            yield (
                "",
                "",
                "",
                "",
                "",
                (
                    f"🛑 Multi-cycle execution stopped before "
                    f"cycle {cycle_index}."
                ),
            )
            return

        cycle_number = next_cycle_number()

        cycle_prefix = (
            f"🔄 Cycle {cycle_number}/{cycle_count}"
        )

        last_result = None

        # --------------------------------------------------------
        # Execute the EXISTING streaming pipeline.
        # --------------------------------------------------------

        for raw_result in run_pipeline_streaming(
            api_url,
            api_key,
            model_name,
            current_thesis,
            temperature,
            max_tokens,
        ):

            result = _extract_streaming_result(raw_result)

            stage_a, stage_b, stage_c, stage_d, stage_e, status = result

            last_result = result

            yield (
                stage_a,
                stage_b,
                stage_c,
                stage_d,
                stage_e,
                f"{cycle_prefix}\n{status}",
            )

        # --------------------------------------------------------
        # Validate completed cycle.
        # --------------------------------------------------------

        if last_result is None:
            raise RuntimeError(
                f"Cycle {cycle_number} produced no streaming result."
            )

        stage_a, stage_b, stage_c, stage_d, stage_e, status = last_result

        if not (stage_a and stage_b and stage_c and stage_d and stage_e):
            raise RuntimeError(
                f"Cycle {cycle_number} completed without all A→E stages."
            )

        # --------------------------------------------------------
        # Persist COMPLETE cycle.
        # --------------------------------------------------------

        save_cycle_stages(
            cycle_number,
            stage_a,
            stage_b,
            stage_c,
            stage_d,
            stage_e,
        )

        # --------------------------------------------------------
        # Persist final E into global synthesis history.
        # --------------------------------------------------------

        append_final_synthesis(
            cycle_number,
            stage_e,
            thesis=current_thesis,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # --------------------------------------------------------
        # Prepare next cycle.
        #
        # Only E is carried forward. Full A→E remains on disk.
        # This prevents the context from growing by all previous
        # cycles indefinitely.
        # --------------------------------------------------------

        current_thesis = (
            f"{current_thesis}\n\n"
            f"Previous cycle final synthesis "
            f"(Cycle {cycle_number}):\n\n"
            f"{stage_e}\n\n"
            f"Continue the analysis from this previous synthesis. "
            f"Critically reassess it, identify weaknesses or "
            f"unresolved contradictions, develop stronger arguments "
            f"and produce a new independent A→E analysis."
        )

        yield (
            stage_a,
            stage_b,
            stage_c,
            stage_d,
            stage_e,
            (
                f"🟢 Cycle {cycle_number} completed and saved.\n"
                f"📁 run_{cycle_number:03d}/\n"
                f"📜 E appended to final_synthesis.txt"
            ),
        )

        if MULTI_CYCLE_STOP_REQUESTED:
            yield (
                stage_a,
                stage_b,
                stage_c,
                stage_d,
                stage_e,
                (
                    f"🛑 Stop requested.\n"
                    f"Cycle {cycle_number} was preserved."
                ),
            )
            return

    yield (
        stage_a,
        stage_b,
        stage_c,
        stage_d,
        stage_e,
        (
            f"✅ All {cycle_count} cycle(s) completed successfully.\n"
            f"📜 Final synthesis history updated."
        ),
    )


# ================================================================
# END PROJECT-1 MULTI-CYCLE ORCHESTRATION v1
# ================================================================




# ================================================================
# PROJECT-1: FINAL SYNTHESIS ONLY UI v1
# ================================================================

def _project1_ui_load_final_synthesis():
    """
    Return the complete accumulated final synthesis history.

    The main UI intentionally displays only this document.
    Individual A-D stages and individual E documents remain
    available through the archive interface.
    """
    try:
        text = load_final_synthesis()
    except Exception as exc:
        return f"⚠️ Unable to load final_synthesis.txt: {exc}"

    if not text:
        return (
            "## Final synthesis history\n\n"
            "_No completed cycles yet._"
        )

    return text


def _project1_ui_cycle_progress(cycle_count):
    """
    Return a compact cycle-progress display.

    This is deliberately independent from the individual
    A→E textboxes.
    """
    try:
        total = int(cycle_count)
    except Exception:
        total = 1

    total = max(1, total)

    completed = len(list_cycles())

    if completed >= total:
        current = total
        state = "✅"
    else:
        current = min(completed + 1, total)
        state = "🔄"

    return (
        f"{state} **Циклы: {completed} / {total}**\n\n"
        f"`{'█' * completed}{'░' * max(0, total - completed)}`"
    )


def _project1_ui_refresh_history():
    """
    Refresh only the accumulated E history document.
    """
    return _project1_ui_load_final_synthesis()


def _project1_ui_refresh_archive():
    """
    Return available cycle numbers for the archive selector.
    """
    cycles = list_cycles()

    if not cycles:
        return gr.update(
            choices=[],
            value=None,
        )

    return gr.update(
        choices=[str(x) for x in cycles],
        value=str(cycles[-1]),
    )


def _project1_ui_load_archive_cycle(cycle_number):
    """
    Load complete A→E data for one selected cycle.

    This function is intentionally isolated from the main
    final-synthesis display.
    """
    if cycle_number in (None, ""):
        return "", "", "", "", ""

    try:
        number = int(cycle_number)
    except Exception:
        return "", "", "", "", ""

    values = []

    for name in (
        "stage_a.txt",
        "stage_b.txt",
        "stage_c.txt",
        "stage_d.txt",
        "stage_e.txt",
    ):
        try:
            value = load_cycle_document(number, name)
        except Exception:
            value = ""

        values.append(value or "")

    return tuple(values)


def _project1_ui_archive_document(cycle_number):
    """
    Load the combined A-E.txt document for the archive.
    """
    if cycle_number in (None, ""):
        return ""

    try:
        number = int(cycle_number)
        value = load_cycle_document(number, "A-E.txt")
        return value or ""
    except Exception as exc:
        return f"⚠️ Unable to load cycle document: {exc}"


def _project1_ui_run_multi_cycle(
    api_url,
    api_key,
    model_name,
    thesis,
    temperature,
    cycle_count,
):
    """
    UI adapter for the existing multi-cycle streaming backend.

    Important:
        - The backend itself remains authoritative.
        - max_tokens is always passed as 25.
        - The main UI receives only cycle progress and the
          accumulated final synthesis history.
    """

    try:
        total = int(cycle_count)
    except Exception:
        total = 1

    total = max(1, total)

    last_history = _project1_ui_load_final_synthesis()

    yield (
        "🔄 **Подготовка цикла 1 / "
        f"{total}**",
        last_history,
    )

    try:
        generator = run_multi_cycle_streaming(
            api_url,
            api_key,
            model_name,
            thesis,
            float(temperature),
            25,
            total,
        )

        completed = 0

        for payload in generator:
            result = _extract_streaming_result(payload)

            if not result:
                continue

            stage_a, stage_b, stage_c, stage_d, stage_e, status = result

            match = re.search(
                r"Cycle\s+(\d+)",
                str(status),
                flags=re.IGNORECASE,
            )

            if match:
                current = int(match.group(1))
            else:
                current = min(completed + 1, total)

            if (
                stage_a
                and stage_b
                and stage_c
                and stage_d
                and stage_e
            ):
                completed = max(completed, current)

            bar_done = min(completed, total)
            bar_left = max(0, total - bar_done)

            progress = (
                f"🔄 **Цикл {current} / {total}**\n\n"
                f"`{'█' * bar_done}"
                f"{'░' * bar_left}`"
            )

            history = _project1_ui_load_final_synthesis()

            yield (
                progress,
                history,
            )

        # --------------------------------------------------------
        # Final refresh after generator completion.
        # --------------------------------------------------------

        final_history = _project1_ui_load_final_synthesis()

        yield (
            f"✅ **Завершено: {total} / {total} циклов**\n\n"
            f"`{'█' * total}`",
            final_history,
        )

    except Exception as exc:
        history = _project1_ui_load_final_synthesis()

        yield (
            f"❌ **Ошибка выполнения:**\n\n{exc}",
            history,
        )

# ================================================================
# PROJECT-1 — COMPATIBLE MULTI-CYCLE UI
# ================================================================

def _project1_ui_load_final_synthesis():
    try:
        if HISTORY_FILE.exists():
            text = HISTORY_FILE.read_text(
                encoding="utf-8"
            ).strip()

            if text:
                return text

        return "Нет сохранённых финальных синтезов."

    except Exception as exc:
        return f"Ошибка чтения final_synthesis.txt: {exc}"


def _project1_ui_load_cycles():
    try:
        cycles = list_cycles()

        if not cycles:
            return "Нет завершённых циклов."

        parts = []

        for cycle in cycles:
            try:
                document = load_cycle_document(cycle)

                parts.append(
                    f"## Cycle {cycle}\n\n"
                    f"{document}"
                )

            except Exception as exc:
                parts.append(
                    f"## Cycle {cycle}\n\n"
                    f"Ошибка загрузки: {exc}"
                )

        return "\n\n---\n\n".join(parts)

    except Exception as exc:
        return f"Ошибка загрузки циклов: {exc}"


def _project1_ui_progress():
    try:
        cycles = list_cycles()

        if not cycles:
            return "### 🔵 Циклы: 0"

        latest = max(cycles)

        cells = []

        for number in cycles:
            cells.append("🟢")

        return (
            f"### Циклы: {len(cycles)}\n\n"
            + " ".join(cells)
            + f"\n\nПоследний завершённый цикл: **{latest}**"
        )

    except Exception as exc:
        return f"Ошибка определения прогресса: {exc}"


def _project1_ui_refresh():
    return (
        _project1_ui_progress(),
        _project1_ui_load_final_synthesis(),
        _project1_ui_load_cycles(),
    )


def _project1_ui_run(
    api_url,
    api_key,
    model_name,
    thesis,
    temperature,
    cycle_count,
):
    """
    UI adapter.

    The backend remains responsible for the actual orchestration.
    max_tokens is intentionally fixed at 25.
    """

    MAX_TOKENS = 25

    try:
        cycle_count_value = int(
            str(cycle_count).strip()
        )
    except Exception:
        cycle_count_value = 1

    if cycle_count_value < 1:
        cycle_count_value = 1

    temperature_value = 0.2

    try:
        temperature_value = float(
            str(temperature).strip()
        )
    except Exception:
        temperature_value = 0.2

    final_result = None

    for result in run_multi_cycle_streaming(
        api_url,
        api_key,
        model_name,
        thesis,
        temperature_value,
        MAX_TOKENS,
        cycle_count_value,
    ):
        final_result = result

        # Streaming is consumed here so the backend executes normally.
        # The main UI intentionally does not expose A→E live.
        pass

    return (
        _project1_ui_progress(),
        _project1_ui_load_final_synthesis(),
        _project1_ui_load_cycles(),
    )


# ================================================================
# GRADIO UI
# ================================================================

with gr.Blocks() as demo:

    gr.Markdown(
        """
# PROJECT-1

Циклический философский анализ.

Основной экран показывает только ход выполнения циклов
и накопленный финальный синтез **E**.

Полные результаты A→E доступны отдельно во вкладке
**Циклы**.
"""
    )

    with gr.Row():

        api_url_ui = gr.Textbox(
            label="API URL",
            placeholder="https://xxxx.trycloudflare.com",
        )

        api_key_ui = gr.Textbox(
            label="API key",
            type="password",
        )

    model_name_ui = gr.Textbox(
        label="Model",
        placeholder="Model name или номер из discovery",
    )

    thesis_ui = gr.Textbox(
        label="Thesis / Query",
        lines=6,
        placeholder="Введите тезис или исследовательский вопрос...",
    )

    with gr.Row():

        temperature_ui = gr.Textbox(
            label="Temperature",
            value="0.2",
        )

        cycle_count_ui = gr.Textbox(
            label="Количество циклов",
            value="2",
        )

    max_tokens_ui = gr.Textbox(
        label="Max tokens / stage",
        value="25",
        interactive=False,
    )

    run_button = gr.Button(
        "🚀 Запустить анализ",
        variant="primary",
    )

    cycle_progress_ui = gr.Markdown(
        _project1_ui_progress()
    )

    gr.Markdown(
        "## Финальный синтез"
    )

    final_synthesis_ui = gr.Markdown(
        _project1_ui_load_final_synthesis()
    )

    with gr.Tab("Циклы"):

        gr.Markdown(
            """
## Полные результаты A→E

Здесь доступны сохранённые документы всех завершённых циклов.
"""
        )

        cycles_ui = gr.Markdown(
            _project1_ui_load_cycles()
        )

        refresh_button = gr.Button(
            "🔄 Обновить результаты"
        )

    run_button.click(
        fn=_project1_ui_run,
        inputs=[
            api_url_ui,
            api_key_ui,
            model_name_ui,
            thesis_ui,
            temperature_ui,
            cycle_count_ui,
        ],
        outputs=[
            cycle_progress_ui,
            final_synthesis_ui,
            cycles_ui,
        ],
    )

    refresh_button.click(
        fn=_project1_ui_refresh,
        inputs=[],
        outputs=[
            cycle_progress_ui,
            final_synthesis_ui,
            cycles_ui,
        ],
    )

