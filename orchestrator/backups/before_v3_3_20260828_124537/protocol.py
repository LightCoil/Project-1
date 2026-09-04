
"""PROJECT-1 Orchestrator protocol v3.1."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PlannerDecision:
    mode: str
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    instruction: str = ""
    raw: Any = None


@dataclass
class ExecutionRecord:
    model: str
    task: str
    status: str
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewDecision:
    action: str
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    instruction: str = ""
    raw: Any = None
