
"""PROJECT-1 local model discovery v2.8."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json


def discover_local_models(
    candidates: List[Path],
) -> List[Dict[str, Any]]:
    """
    Convert discovered model directories into registry descriptions.

    This function performs discovery only.
    It does NOT load model weights.
    """

    result = []

    for path in candidates:
        path = Path(path)

        if not path.exists():
            continue

        config_path = path / "config.json"

        config = {}

        if config_path.exists():
            try:
                config = json.loads(
                    config_path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                config = {}

        name = path.name

        model_type = config.get(
            "model_type"
        )

        architectures = config.get(
            "architectures",
            [],
        )

        capabilities = [
            "general",
            "analysis",
        ]

        architecture_text = " ".join(
            str(x)
            for x in architectures
        ).lower()

        if any(
            word in architecture_text
            for word in (
                "coder",
                "code",
                "qwen2",
                "qwen3",
            )
        ):
            capabilities.extend(
                [
                    "code",
                    "software_engineering",
                ]
            )

        result.append(
            {
                "name": name,
                "provider": "local",
                "description": (
                    f"Discovered local model: {name}"
                ),
                "path": str(path),
                "model_type": model_type,
                "architectures": architectures,
                "capabilities": sorted(
                    set(capabilities)
                ),
                "context_window": int(
                    config.get(
                        "max_position_embeddings",
                        8192,
                    )
                    or 8192
                ),
                "max_output_tokens": 25,
                "supports_streaming": True,
                "supports_reasoning": (
                    "reasoning" in capabilities
                ),
                "supports_code": (
                    "code" in capabilities
                ),
                "executable": False,
            }
        )

    return result
