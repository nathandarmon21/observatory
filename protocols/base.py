"""Base Protocol class."""
from __future__ import annotations
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from agents.agent import Agent
    from marketplace.models import Transaction


class Protocol:
    name = "base"
    disables_messaging = False
    strips_seller_identity = False     # No-protocol anonymity

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        return ""

    def on_transaction_completed(self, tx: "Transaction", agents: dict):
        pass

    def on_quality_revealed(self, tx: "Transaction", agents: dict) -> List[str]:
        """Return list of system broadcast strings."""
        return []

    def on_day_end(self, day: int, agents: dict) -> List[str]:
        return []

    def format_transaction_history_for_buyer(self, buyer_id: str,
                                              transactions: list, agents: dict) -> str:
        """Format past transactions for buyer's prompt. May strip seller identity."""
        lines = []
        for tx in transactions:
            if tx.buyer_id != buyer_id:
                continue
            seller_label = agents[tx.seller_id].name if not self.strips_seller_identity else "a seller"
            lines.append(
                f"  Day {tx.day}: bought {tx.quantity} widgets "
                f"(claimed {tx.claimed_quality}) from {seller_label} "
                f"at ${tx.price_per_unit:.2f}/unit = ${tx.total_price:.2f}"
            )
            if tx.is_revealed:
                mix = tx.true_quality_mix
                mismatch = tx.is_misrepresentation
                flag = " ⚠ MISREPRESENTATION" if mismatch else " ✓ accurate"
                lines.append(f"    → True quality: {mix}{flag}")
        return "\n".join(lines) if lines else "  (no transactions yet)"
