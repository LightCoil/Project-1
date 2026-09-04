from __future__ import annotations

from pathlib import Path
from typing import Any


class ListFilesTool:

    name = "list_files"

    description = (
        "List files and directories inside the workspace."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Directory relative to the workspace. "
                    "Use '.' for the workspace root."
                ),
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    def __init__(
        self,
        workspace,
    ):

        self.workspace = (
            Path(workspace)
            .resolve()
        )

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> str:

        relative_path = arguments.get(
            "path",
            ".",
        )

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
                f"Path not found: {relative_path}"
            )

        if not path.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {relative_path}"
            )

        entries = []

        for item in sorted(
            path.iterdir(),
            key=lambda p: (
                not p.is_dir(),
                p.name.lower(),
            ),
        ):

            relative = (
                item.relative_to(
                    self.workspace
                )
            )

            if item.is_dir():

                entries.append(
                    f"[DIR]  {relative}/"
                )

            else:

                entries.append(
                    f"[FILE] {relative}"
                )

        if not entries:

            return "(empty directory)"

        return "\n".join(entries)
