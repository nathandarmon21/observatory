"""Marketplace models for The Sanctuary widget economy."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict

def _uid() -> str:
    return str(uuid.uuid4())[:8]

@dataclass
class Widget:
    id: str = field(default_factory=_uid)
    seller_id: str = ""
    quality: str = "excellent"          # "excellent" | "poor" — true quality, seller knows
    production_cost: float = 30.0       # what it cost to make
    fair_market_value: float = 55.0     # reference value for surplus calculation
    day_produced: int = 0
    holding_cost_paid: float = 0.0
    is_sold: bool = False
    # Listing info (set when seller commits to a deal)
    listed_quality: str = ""            # what seller claimed to buyer
    listed_price: float = 0.0

    def daily_holding_cost(self) -> float:
        """2% of production cost per day."""
        return self.production_cost * 0.02

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "quality": self.quality,
            "production_cost": round(self.production_cost, 2),
            "cost": round(self.production_cost, 2),           # alias expected by frontend
            "fair_market_value": round(self.fair_market_value, 2),
            "day_produced": self.day_produced,
            "holding_cost_paid": round(self.holding_cost_paid, 2),
            "is_sold": self.is_sold,
            "listed_quality": self.listed_quality,
            "listed_price": round(self.listed_price, 2),
            "listed": self.listed_price > 0,
            "spec_summary": f"{self.quality.capitalize()} widget (Day {self.day_produced})",
            "condition": self.quality,                        # alias expected by frontend
        }


@dataclass
class Factory:
    id: str = field(default_factory=_uid)
    seller_id: str = ""
    day_ordered: int = 0
    operational_day: int = 0    # day_ordered + 3
    is_operational: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "day_ordered": self.day_ordered,
            "operational_day": self.operational_day,
            "is_operational": self.is_operational,
        }


@dataclass
class Transaction:
    id: str = field(default_factory=_uid)
    seller_id: str = ""
    buyer_id: str = ""
    widget_ids: List[str] = field(default_factory=list)
    quantity: int = 0
    price_per_unit: float = 0.0
    total_price: float = 0.0
    claimed_quality: str = ""       # what seller told buyer
    day: int = 0
    reveal_day: int = 0             # day + 5
    is_revealed: bool = False
    true_quality_mix: Dict[str, int] = field(default_factory=dict)  # {"excellent": N, "poor": M}
    is_misrepresentation: bool = False
    seller_surplus: float = 0.0     # total_price - sum(production_costs)
    buyer_surplus: float = 0.0      # sum(fair_market_values) - total_price

    def to_dict(self) -> dict:
        mix_str = ", ".join(f"{v}x {k}" for k, v in self.true_quality_mix.items()) if self.true_quality_mix else ""
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "buyer_id": self.buyer_id,
            "widget_ids": self.widget_ids,
            "quantity": self.quantity,
            "price_per_unit": round(self.price_per_unit, 2),
            "price": round(self.price_per_unit, 2),       # alias expected by frontend
            "total_price": round(self.total_price, 2),
            "claimed_quality": self.claimed_quality,
            "spec_summary": f"{self.quantity}x widget, claimed {self.claimed_quality}" + (f" | true: {mix_str}" if self.is_revealed and mix_str else ""),
            "day": self.day,
            "reveal_day": self.reveal_day,
            "is_revealed": self.is_revealed,
            "true_quality_mix": self.true_quality_mix,
            "is_misrepresentation": self.is_misrepresentation,
            "seller_surplus": round(self.seller_surplus, 2),
            "buyer_surplus": round(self.buyer_surplus, 2),
        }


@dataclass
class Message:
    id: str = field(default_factory=_uid)
    sender_id: str = ""
    sender_name: str = ""
    recipient_id: str = ""          # agent id or "public_forum"
    content: str = ""
    day: int = 0
    round: int = 0                  # negotiation round within the day
    is_public: bool = False
    channel: str = ""               # 'sale' | 'quality' | 'private' | 'public' | 'system'

    def to_dict(self) -> dict:
        if self.channel:
            ch = self.channel
        elif self.is_public:
            ch = "public"
        elif self.sender_id == "system":
            ch = "system"
        else:
            ch = "private"
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "body": self.content,
            "channel": ch,
            "day": self.day,
            "round": self.round,
            "is_public": self.is_public,
        }


@dataclass
class PendingDeal:
    """A proposed transaction waiting for counterparty acceptance."""
    proposer_id: str = ""
    counterparty_id: str = ""
    quantity: int = 0
    price_per_unit: float = 0.0
    total_price: float = 0.0
    claimed_quality: str = ""
    day: int = 0
    round_proposed: int = 0
    accepted: bool = False

    def to_dict(self) -> dict:
        return {
            "proposer_id": self.proposer_id,
            "counterparty_id": self.counterparty_id,
            "quantity": self.quantity,
            "price_per_unit": round(self.price_per_unit, 2),
            "total_price": round(self.total_price, 2),
            "claimed_quality": self.claimed_quality,
        }
