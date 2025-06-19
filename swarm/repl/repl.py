# Simplified REPL implementation used for demo purposes.
from typing import Callable, List


class Swarm:
    """Minimal container for multiple agents."""

    def __init__(self, agents: List[object] | None = None):
        self.agents = agents or []

    def add_agent(self, agent: object) -> None:
        self.agents.append(agent)


def run_demo_loop(agent: object, booluser_simulation: bool = False, useragent: object | None = None,
                   booldebug: bool = False, use_translation: bool = False) -> None:
    """Run a very simple REPL loop for the given agent.

    Parameters mirror the original interface but are mostly ignored in this
    placeholder implementation.
    """
    print(f"Starting demo loop for {getattr(agent, 'name', 'Agent')}. Type 'exit' to quit.")
    available_funcs = {fn.__name__: fn for fn in getattr(agent, 'functions', [])}
    while True:
        try:
            user_input = input('> ').strip()
        except EOFError:
            break
        if user_input.lower() in {'exit', 'quit'}:
            break
        if user_input in available_funcs:
            try:
                result = available_funcs[user_input]()
                print(result)
            except Exception as exc:
                print(f"Error running {user_input}: {exc}")
        else:
            print(f"Unknown command: {user_input}")

