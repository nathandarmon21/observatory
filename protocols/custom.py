from protocols.base import Protocol


class CustomProtocol(Protocol):
    name = "custom"

    def __init__(self, description: str = ""):
        self.custom_description = description

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        if self.custom_description:
            return f"ACTIVE PROTOCOL (custom):\n{self.custom_description}"
        return ""
