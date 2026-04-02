import random
from protocols.base import Protocol
from typing import List


class MandatoryAuditProtocol(Protocol):
    name = "mandatory_audit"
    AUDIT_PROB = 0.25
    PENALTY_RATE = 0.25

    def on_transaction_completed(self, tx, agents: dict):
        if random.random() < self.AUDIT_PROB:
            tx.is_audited = True
            if tx.is_misrepresentation:
                penalty = tx.total_price * self.PENALTY_RATE
                if tx.seller_id in agents:
                    agents[tx.seller_id].balance -= penalty
                    agents[tx.seller_id].total_revenue -= penalty

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        return "ACTIVE PROTOCOL: Mandatory Audit. 25% of transactions are randomly inspected before delivery. If misrepresentation is found, seller pays a 25% penalty on the transaction value."

    def on_quality_revealed(self, tx, agents: dict) -> List[str]:
        msgs = []
        if getattr(tx, "is_audited", False) and tx.is_misrepresentation:
            seller = agents.get(tx.seller_id)
            penalty = tx.total_price * self.PENALTY_RATE
            msgs.append(f"AUDIT RESULT: {seller.name if seller else tx.seller_id} misrepresented quality. Penalty: ${penalty:.2f}")
        return msgs
