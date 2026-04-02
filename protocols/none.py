"""No Protocol — pure free market baseline."""
from .base import Protocol


class NoProtocol(Protocol):
    name = "no_protocol"
    description = "Pure free market. No reputation system, no auditing, no oversight. Agents rely only on their own experience and private communication."

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        return ""
