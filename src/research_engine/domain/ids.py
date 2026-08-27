from __future__ import annotations

import secrets


def new_id(prefix: str) -> str:
    """Stable unique id that does not depend on row counts, e.g. exp_a1b2c3d4e5f6g7h8."""
    return f"{prefix}_{secrets.token_hex(8)}"


def format_research_number(number: int, research_count: int) -> str:
    width = max(3, len(str(research_count)))
    return str(number).zfill(width)
