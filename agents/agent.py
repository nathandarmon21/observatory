"""Agent class for The Sanctuary widget economy."""
from __future__ import annotations
from typing import List, Dict, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from marketplace.models import Widget

# Production cost table by factory count
PRODUCTION_COSTS = {
    "excellent": {1: 30.0, 2: 27.0, 3: 24.60, 4: 22.80},
    "poor":      {1: 20.0, 2: 18.0, 3: 16.40, 4: 15.20},
}
FAIR_MARKET_VALUE = {"excellent": 55.0, "poor": 32.0}


def get_production_cost(quality: str, factory_count: int) -> float:
    costs = PRODUCTION_COSTS[quality]
    key = min(factory_count, 4)
    return costs.get(key, costs[4])


class Agent:
    def __init__(self, agent_id: str, name: str, role: str,
                 starting_cash: float, quota: int = 0):
        self.id = agent_id
        self.name = name
        self.role = role                    # "seller" | "buyer"
        self.balance = starting_cash
        self.starting_balance = starting_cash
        self.is_bankrupt = False

        # Persistent LLM conversation thread
        self.messages: List[dict] = []      # OpenAI chat format
        self.system_prompt: str = ""

        # Inbox (messages received today, cleared each day)
        self.inbox: List[dict] = []

        # Seller state
        self.inventory: List["Widget"] = []
        self.factories: int = 0             # operational factories
        self.factories_under_construction: List[dict] = []  # [{ordered_day, ready_day}]
        self.total_revenue: float = 0.0
        self.total_production_costs: float = 0.0
        self.total_holding_costs: float = 0.0
        self.total_factory_investments: float = 0.0
        self.transaction_today: bool = False  # max 1 transaction per day

        # Buyer state
        self.quota: int = quota
        self.acquired: int = 0
        self.total_spent: float = 0.0
        self.total_fair_value_acquired: float = 0.0
        self.total_penalties: float = 0.0
        self.transaction_today_buyer: bool = False

        # Tracking
        self.reasoning_log: List[dict] = []
        self.strategy_notes: str = ""
        self.quality_accuracy_log: List[bool] = []  # True if honest, False if misrep (sellers)
        self.inactive_days: int = 0                  # consecutive days with no action
        self.balance_history: List[dict] = []        # [{day, balance}] for chart persistence

    # ── Seller helpers ────────────────────────────────────────────────────────

    @property
    def operational_factories(self) -> int:
        return self.factories

    @property
    def production_capacity(self) -> int:
        """Max widgets producible per day."""
        return self.factories

    @property
    def net_profit(self) -> float:
        return (self.total_revenue
                - self.total_production_costs
                - self.total_holding_costs
                - self.total_factory_investments)

    @property
    def inventory_count(self) -> int:
        return len([w for w in self.inventory if not w.is_sold])

    @property
    def quality_accuracy(self) -> float:
        if not self.quality_accuracy_log:
            return 1.0
        return sum(self.quality_accuracy_log) / len(self.quality_accuracy_log)

    def current_production_cost(self, quality: str) -> float:
        return get_production_cost(quality, self.factories)

    # ── Buyer helpers ─────────────────────────────────────────────────────────

    @property
    def remaining_quota(self) -> int:
        return max(0, self.quota - self.acquired)

    @property
    def daily_penalty(self) -> float:
        return self.remaining_quota * 2.0

    @property
    def seller_value_differential(self) -> float:
        """Revenue minus production costs and factory investments (excludes holding costs)."""
        return self.total_revenue - self.total_production_costs - self.total_factory_investments

    @property
    def value_differential(self) -> float:
        return self.total_fair_value_acquired - self.total_spent

    # ── Shared ────────────────────────────────────────────────────────────────

    def receive_message(self, sender_id: str, sender_name: str,
                        content: str, day: int, round_: int = 0,
                        is_public: bool = False):
        self.inbox.append({
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "day": day,
            "round": round_,
            "is_public": is_public,
        })

    def flush_inbox(self) -> List[dict]:
        msgs = list(self.inbox)
        self.inbox = []
        return msgs

    def log_reasoning(self, day: int, reasoning: str, action_summary: str):
        self.reasoning_log.append({
            "day": day,
            "reasoning": reasoning,
            "action": action_summary,
        })
        if len(self.reasoning_log) > 200:
            self.reasoning_log = self.reasoning_log[-200:]

    def to_dict(self) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "balance": round(self.balance, 2),
            "starting_balance": round(self.starting_balance, 2),
            "is_bankrupt": self.is_bankrupt,
            "strategy_notes": self.strategy_notes,
            "reasoning_log": self.reasoning_log[-30:],
            "inactive_days": self.inactive_days,
            "balance_history": self.balance_history[-60:],
        }
        if self.role == "seller":
            np = round(self.net_profit, 2)
            base.update({
                "factories": self.factories,
                "factories_under_construction": self.factories_under_construction,
                "inventory_count": self.inventory_count,
                "total_revenue": round(self.total_revenue, 2),
                "total_production_costs": round(self.total_production_costs, 2),
                "total_holding_costs": round(self.total_holding_costs, 2),
                "total_factory_investments": round(self.total_factory_investments, 2),
                "net_profit": np,
                "profit": np,                           # alias expected by frontend modal
                "value_differential": round(self.seller_value_differential, 2),
                "quality_accuracy": round(self.quality_accuracy, 3),
                "production_capacity": self.production_capacity,
                "specialty": "Widget Manufacturing",    # expected by frontend modal
            })
        else:
            base.update({
                "quota": self.quota,
                "acquired": self.acquired,
                "remaining_quota": self.remaining_quota,
                "daily_penalty": round(self.daily_penalty, 2),
                "total_spent": round(self.total_spent, 2),
                "total_fair_value_acquired": round(self.total_fair_value_acquired, 2),
                "total_penalties": round(self.total_penalties, 2),
                "value_differential": round(self.value_differential, 2),
                "specialty": "Widget Procurement",      # expected by frontend modal
                "profit": round(-self.total_spent - self.total_penalties, 2),
            })
        return base
