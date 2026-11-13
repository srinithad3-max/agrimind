from __future__ import annotations

from app.core.blackboard import Blackboard


class Agent:
    """Base class. Each agent declares what it reads and what it publishes."""
    id: str = "agent"
    name: str = "Agent"
    icon: str = "•"
    reads: list[str] = []
    publishes: list[str] = []

    def __init__(self, bb: Blackboard):
        self.bb = bb

    def say(self, text: str, to: str = "all", level: str = "info"):
        self.bb.message(self.id, text, to=to, level=level)

    def run(self) -> dict:
        raise NotImplementedError

    # Optional second round: react to what other agents published
    def react(self) -> None:
        return None
