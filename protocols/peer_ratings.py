from protocols.base import Protocol
from typing import List


class PeerRatingsProtocol(Protocol):
    name = "peer_ratings"

    def __init__(self):
        self._ratings: dict = {}   # seller_id -> list of ratings (1-5)

    def on_quality_revealed(self, tx, agents: dict) -> List[str]:
        if tx.buyer_id not in agents or tx.seller_id not in agents:
            return []
        if tx.is_misrepresentation:
            self._ratings.setdefault(tx.seller_id, []).append(1)
        else:
            self._ratings.setdefault(tx.seller_id, []).append(5)
        avg = sum(self._ratings[tx.seller_id]) / len(self._ratings[tx.seller_id])
        seller_name = agents[tx.seller_id].name
        return [f"Peer rating updated: {seller_name} now {avg:.1f}/5 stars ({len(self._ratings[tx.seller_id])} ratings)"]

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        lines = []
        for sid, ratings in self._ratings.items():
            if sid in agents:
                avg = sum(ratings) / len(ratings)
                lines.append(f"  {agents[sid].name}: {avg:.1f}/5 ({len(ratings)} ratings)")
        summary = "\n".join(lines) if lines else "  (no ratings yet)"
        return f"ACTIVE PROTOCOL: Peer Ratings.\nPublic seller ratings:\n{summary}"
