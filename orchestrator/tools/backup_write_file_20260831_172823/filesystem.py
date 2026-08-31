
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


class SearchCodeTool:
    """
    Search for a text fragment inside source files.

    The search is intentionally simple and deterministic in V1.
    """

    name = "search_code"

    description = (
        "Search for a text fragment inside source files "
        "in the workspace."
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
                    "Directory or file relative to workspace."
                ),
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    IGNORED_DIRS = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
    }

    TEXT_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
        ".html",
        ".css",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".java",
        ".go",
        ".rs",
        ".sh",
    }

    def __init__(
        self,
        workspace: str | Path,
    ):
        self.workspace = Path(
            workspace
        ).resolve()

    def _safe_path(
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

    def execute(
        self,
        arguments: dict,
    ) -> str:

        query = arguments["query"]
        relative_path = arguments.get(
            "path",
            ".",
        )

        if not query:
            raise ValueError(
                "Search query cannot be empty."
            )

        root = self._safe_path(
            relative_path
        )

        if not root.exists():
            raise FileNotFoundError(
                f"Path not found: {relative_path}"
            )

        files = []

        if root.is_file():
            files.append(root)

        else:
            for path in root.rglob("*"):

                if not path.is_file():
                    continue

                if any(
                    ignored in path.parts
                    for ignored in self.IGNORED_DIRS
                ):
                    continue

                if (
                    path.suffix.lower()
                    not in self.TEXT_EXTENSIONS
                ):
                    continue

                files.append(path)

        results = []

        for path in sorted(files):

            try:
                text = path.read_text(
                    encoding="utf-8"
                )
            except (
                UnicodeDecodeError,
                OSError,
            ):
                continue

            for line_no, line in enumerate(
                text.splitlines(),
                start=1,
            ):

                if query in line:

                    relative = path.relative_to(
                        self.workspace
                    )

                    results.append(
                        f"{relative}:{line_no}: {line.strip()}"
                    )

        if not results:
            return "No matches found."

        return "\n".join(results)
