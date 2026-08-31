from __future__ import annotations

from pathlib import Path


class ReadFileTool:
    """
    Read a text file from the workspace.
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
        "additionalProperties": False,
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

        relative_path = arguments["path"]

        path = (
            self.workspace
            / relative_path
        ).resolve()

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


class WriteFileTool:
    """
    Write text content to a file inside the workspace.

    V1:
    - workspace boundary enforced
    - parent directories created automatically
    - UTF-8 encoding
    - file overwrite allowed
    """

    name = "write_file"

    description = (
        "Write text content to a file inside the workspace."
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
            "content": {
                "type": "string",
                "description": (
                    "Complete text content to write."
                ),
            },
        },
        "required": [
            "path",
            "content",
        ],
        "additionalProperties": False,
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

        content = arguments[
            "content"
        ]

        path = (
            self.workspace
            / relative_path
        ).resolve()

        # -------------------------------------------------------------
        # WORKSPACE BOUNDARY
        # -------------------------------------------------------------

        if (
            path != self.workspace
            and self.workspace not in path.parents
        ):
            raise PermissionError(
                "Path escapes workspace."
            )

        # -------------------------------------------------------------
        # DIRECTORY
        # -------------------------------------------------------------

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -------------------------------------------------------------
        # WRITE
        # -------------------------------------------------------------

        path.write_text(
            content,
            encoding="utf-8",
        )

        return (
            f"File written successfully: "
            f"{relative_path}"
        )
