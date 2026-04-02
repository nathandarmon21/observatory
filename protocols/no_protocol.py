from protocols.base import Protocol


class NoProtocol(Protocol):
    name = "no_protocol"
    strips_seller_identity = True   # Buyers don't remember which seller deceived them

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        return "ACTIVE PROTOCOL: No Protocol (Baseline). No reputation system. No auditing. Buyer transaction history does NOT record seller names."
