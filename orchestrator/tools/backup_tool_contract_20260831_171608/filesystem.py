
from __future__ import annotations

from pathlib import Path


class ReadFileTool:
    """
    Read a text file from the workspace.

    V0.1 intentionally keeps the implementation simple.
    Permission boundaries and workspace sandboxing will be
    added by the Tool Registry.
    """

    name = "read_file"

    description = (
        "Read the contents of a text file."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path relative to the workspace."
                ),
            },
        },
        "required": ["path"],
    }

    def __init__(
        self,
        workspace: str | Path,
    ):
        self.workspace = Path(
            workspace
        ).resolve()

    def execute(
        self,
        arguments: dict,
    ) -> str:

        relative_path = arguments[
            "path"
        ]

        path = (
            self.workspace
            / relative_path
        ).resolve()

        # Basic workspace boundary.
        if (
            path != self.workspace
            and self.workspace not in path.parents
        ):
            raise PermissionError(
                "Path escapes workspace."
            )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {relative_path}"
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"Not a file: {relative_path}"
            )

        return path.read_text(
            encoding="utf-8"
        )
