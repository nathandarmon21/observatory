"""Build the 4-agent cast for The Sanctuary widget economy."""
from __future__ import annotations
import random
from agents.agent import Agent, get_production_cost, FAIR_MARKET_VALUE
from marketplace.models import Widget


def build_cast(seed: int = 42) -> dict:
    """Return dict of agent_id -> Agent with starting inventories."""
    rng = random.Random(seed)

    aragorn = Agent("aragorn", "Aragorn", "seller", starting_cash=5000.0)
    aragorn.factories = 1

    saruman = Agent("saruman", "Saruman", "seller", starting_cash=4000.0)
    saruman.factories = 1

    galadriel = Agent("galadriel", "Galadriel", "buyer",
                      starting_cash=8000.0, quota=40)
    gimli = Agent("gimli", "Gimli", "buyer",
                  starting_cash=6000.0, quota=40)

    # Give each seller 10 starting widgets (random quality mix)
    for seller in [aragorn, saruman]:
        for _ in range(10):
            quality = rng.choice(["excellent", "poor"])
            cost = get_production_cost(quality, seller.factories)
            fmv = FAIR_MARKET_VALUE[quality]
            w = Widget(
                seller_id=seller.id,
                quality=quality,
                production_cost=cost,
                fair_market_value=fmv,
                day_produced=0,
            )
            seller.inventory.append(w)
        # Starting inventory is an endowment — don't charge production costs
        # so net_profit starts at 0 rather than immediately negative

    return {
        "aragorn": aragorn,
        "saruman": saruman,
        "galadriel": galadriel,
        "gimli": gimli,
    }
