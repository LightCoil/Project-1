from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderResponse:
    provider: str
    content: str
    success: bool = True
    metadata: dict | None = None


class ModelProvider(Protocol):
    """
    Generic interface for any reasoning/model provider.

    A provider may represent:
      - local EXL2 model
      - local transformers model
      - ChatGPT
      - another API model
      - future autonomous worker
    """

    name: str

    def ask(self, instruction: str) -> ProviderResponse:
        ...


class StubProvider:
    """
    Safe development provider.

    It performs NO external request and NO model execution.
    """

    def __init__(self, name: str):
        self.name = name

    def ask(self, instruction: str) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            content=(
                "[STUB RESPONSE]\n"
                "No model was contacted.\n\n"
                f"Instruction received:\n{instruction}"
            ),
            success=True,
            metadata={
                "execution": "stub",
            },
        )
