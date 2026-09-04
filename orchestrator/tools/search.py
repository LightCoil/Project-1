from __future__ import annotations

from pathlib import Path
from typing import Any


class SearchCodeTool:
    """
    Search text inside files in the workspace.

    V1:
    - workspace boundary enforced;
    - recursive search;
    - plain text substring matching;
    - optional relative path;
    - result limit;
    - binary files skipped.
    """

    name = "search_code"

    description = (
        "Search for a text string inside files in the workspace. "
        "Returns matching file paths, line numbers, and lines."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Text to search for."
                ),
            },
            "path": {
                "type": "string",
                "description": (
                    "Optional file or directory relative "
                    "to the workspace. Use '.' for the root."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": (
                    "Maximum number of matching lines to return."
                ),
            },
        },
        "required": [
            "query",
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

    def _resolve_inside_workspace(
        self,
        relative_path: str,
    ) -> Path:

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

        return path

    def _is_probably_binary(
        self,
        path: Path,
    ) -> bool:

        try:

            sample = path.read_bytes()[:4096]

        except OSError:

            return True

        return b"\x00" in sample

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> str:

        query = arguments.get(
            "query"
        )

        if not isinstance(
            query,
            str,
        ):
            raise TypeError(
                "query must be a string."
            )

        if not query:
            raise ValueError(
                "query cannot be empty."
            )

        relative_path = arguments.get(
            "path",
            ".",
        )

        if not isinstance(
            relative_path,
            str,
        ):
            raise TypeError(
                "path must be a string."
            )

        max_results = arguments.get(
            "max_results",
            50,
        )

        if not isinstance(
            max_results,
            int,
        ) or isinstance(
            max_results,
            bool,
        ):
            raise TypeError(
                "max_results must be an integer."
            )

        if max_results <= 0:
            raise ValueError(
                "max_results must be greater than zero."
            )

        search_root = self._resolve_inside_workspace(
            relative_path
        )

        if not search_root.exists():
            raise FileNotFoundError(
                f"Path not found: {relative_path}"
            )

        if search_root.is_file():

            files = [search_root]

        elif search_root.is_dir():

            files = [
                path
                for path in search_root.rglob("*")
                if path.is_file()
            ]

            files.sort(
                key=lambda path: str(
                    path.relative_to(
                        self.workspace
                    )
                ).lower()
            )

        else:

            raise ValueError(
                f"Unsupported path: {relative_path}"
            )

        results = []

        for path in files:

            if len(results) >= max_results:
                break

            if self._is_probably_binary(path):
                continue

            try:

                text = path.read_text(
                    encoding="utf-8"
                )

            except (
                UnicodeDecodeError,
                OSError,
            ):

                continue

            relative = path.relative_to(
                self.workspace
            )

            for line_number, line in enumerate(
                text.splitlines(),
                start=1,
            ):

                if query in line:

                    results.append(
                        f"{relative}:{line_number}: {line}"
                    )

                    if len(results) >= max_results:
                        break

        if not results:

            return (
                f"No matches found for query: {query!r}"
            )

        output = "\n".join(results)

        if len(results) >= max_results:

            output += (
                "\n"
                f"[results truncated at {max_results}]"
            )

        return output
