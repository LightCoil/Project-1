from __future__ import annotations

import subprocess
import shlex
from typing import Any


class RunCommandTool:

    name = "run_command"

    description = (
        "Run a safe command inside the workspace. "
        "Only pytest, python, and python3 are allowed."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "Command to execute."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": (
                    "Maximum execution time in seconds."
                ),
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    ALLOWED_PROGRAMS = {
        "pytest",
        "python",
        "python3",
    }

    FORBIDDEN_OPERATORS = [
        "&&",
        "||",
        ";",
        "|",
        ">",
        "<",
        "`",
        "$(",
    ]

    def __init__(
        self,
        workspace,
    ):

        from pathlib import Path

        self.workspace = (
            Path(workspace)
            .resolve()
        )

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> str:

        command = arguments.get(
            "command"
        )

        if not isinstance(
            command,
            str,
        ):

            raise TypeError(
                "command must be a string."
            )

        timeout = arguments.get(
            "timeout",
            60,
        )

        if not isinstance(
            timeout,
            int,
        ):

            raise TypeError(
                "timeout must be an integer."
            )

        if timeout <= 0:

            raise ValueError(
                "timeout must be greater than zero."
            )

        # -------------------------------------------------------------
        # Shell operators
        # -------------------------------------------------------------

        for operator in (
            self.FORBIDDEN_OPERATORS
        ):

            if operator in command:

                raise PermissionError(
                    f"Shell operator not allowed: {operator}"
                )

        # -------------------------------------------------------------
        # Parse without shell
        # -------------------------------------------------------------

        try:

            parts = shlex.split(
                command
            )

        except ValueError as exc:

            raise ValueError(
                f"Invalid command syntax: {exc}"
            ) from exc

        if not parts:

            raise ValueError(
                "Command cannot be empty."
            )

        program = parts[0]

        if program not in self.ALLOWED_PROGRAMS:

            raise PermissionError(
                "Command not allowed: "
                f"{program}. "
                "Allowed programs: "
                "pytest, python, python3"
            )

        # -------------------------------------------------------------
        # Execute
        # -------------------------------------------------------------

        try:

            result = subprocess.run(
                parts,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

        except subprocess.TimeoutExpired as exc:

            raise RuntimeError(
                f"Command timed out after {timeout} seconds."
            ) from exc

        return (
            f"exit_code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
