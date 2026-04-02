from protocols.base import Protocol


class CreditBureauProtocol(Protocol):
    name = "credit_bureau"

    def __init__(self):
        self._scores: dict = {}  # seller_id -> score (0-100)

    def _update_scores(self, agents: dict, transactions: list):
        for agent_id, agent in agents.items():
            if agent.role != "seller":
                continue
            acc = agent.quality_accuracy
            self._scores[agent_id] = round(acc * 100)

    def get_agent_context(self, agent_id: str, agents: dict) -> str:
        scores = "\n".join(
            f"  {agents[sid].name}: {score}/100"
            for sid, score in self._scores.items()
            if sid in agents
        )
        return f"ACTIVE PROTOCOL: Centralized Reputation (Credit Bureau).\nCurrent reliability scores:\n{scores or '  (not yet computed)'}"

    def on_day_end(self, day: int, agents: dict):
        self._update_scores(agents, [])
        return []
