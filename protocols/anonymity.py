from protocols.base import Protocol


class AnonymityProtocol(Protocol):
    name = "anonymity"
    disables_messaging = True
    strips_seller_identity = True

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        return "ACTIVE PROTOCOL: Full Anonymity. You cannot identify other agents. No private messaging. No forum. Every transaction is with an unknown counterparty."
