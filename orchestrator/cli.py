from .core import Orchestrator
from .providers import StubProvider


def build_development_orchestrator() -> Orchestrator:
    """
    Development configuration.

    No real API is used here.
    """

    providers = {
        "chatgpt": StubProvider("chatgpt"),
        "local_model": StubProvider("local_model"),
    }

    return Orchestrator(
        providers=providers
    )


def main() -> None:
    task = input("PROJECT-1 task: ").strip()

    orchestrator = build_development_orchestrator()

    state = orchestrator.create_task(task)

    print("\nTask accepted.")
    print("Providers:", ", ".join(orchestrator.providers))
    print("State created.")

    orchestrator.save_state(state)

    print("State saved.")


if __name__ == "__main__":
    main()
