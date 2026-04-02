"""Narrative event detector for The Sanctuary."""
from __future__ import annotations
import statistics
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class NarrativeEvent:
    event_type: str
    title: str
    description: str
    agents_involved: List[str]
    day: int
    phase: int
    severity: str = "info"   # info / warning / critical
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "agents_involved": self.agents_involved,
            "day": self.day,
            "phase": self.phase,
            "severity": self.severity,
            "evidence": self.evidence,
        }


class NarrativeDetector:
    """Detects emergent patterns and generates story-level events."""

    def __init__(self):
        self._events: List[NarrativeEvent] = []
        self._last_check_phase: Dict[str, int] = {}

    def detect(self, agents: dict, contracts: List, phase: int, day: int,
               messages: List = None) -> List[NarrativeEvent]:
        new_events = []
        new_events += self._check_dominance(agents, contracts, phase, day)
        new_events += self._check_fraud_streak(agents, contracts, phase, day)
        new_events += self._check_bankruptcy_risk(agents, phase, day)
        new_events += self._check_price_gouging(agents, contracts, phase, day)
        new_events += self._check_trust_collapse(agents, phase, day)
        new_events += self._check_quality_race(agents, contracts, phase, day)
        if messages:
            new_events += self._check_communication_patterns(agents, messages, phase, day)
        self._events.extend(new_events)
        return new_events

    def _check_dominance(self, agents: dict, contracts: List, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("dominance", 0) > phase - 9:
            return []
        self._last_check_phase["dominance"] = phase

        counts = defaultdict(int)
        for c in contracts:
            if hasattr(c, 'agent_id'):
                counts[c.agent_id] += 1
        if not counts:
            return []

        total = sum(counts.values())
        events = []
        for agent_id, count in counts.items():
            share = count / total
            if share > 0.45 and total >= 5:
                agent = agents.get(agent_id)
                name = agent.name if agent else agent_id
                events.append(NarrativeEvent(
                    event_type="market_dominance",
                    title=f"{name} controls the market",
                    description=f"{name} has completed {count} of {total} contracts ({share:.0%}) — a near-monopoly. Other agents may struggle to win work.",
                    agents_involved=[agent_id],
                    day=day, phase=phase, severity="warning",
                    evidence={"share": share, "contracts": count},
                ))
        return events

    def _check_fraud_streak(self, agents: dict, contracts: List, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("fraud", 0) > phase - 6:
            return []
        self._last_check_phase["fraud"] = phase

        from marketplace.models import ContractStatus
        fraud_by_agent = defaultdict(list)
        for c in contracts[-30:]:
            if c.status == ContractStatus.DISPUTED:
                fraud_by_agent[c.agent_id].append(c)

        events = []
        for agent_id, frauds in fraud_by_agent.items():
            if len(frauds) >= 3:
                agent = agents.get(agent_id)
                name = agent.name if agent else agent_id
                events.append(NarrativeEvent(
                    event_type="fraud_streak",
                    title=f"{name} is running a long con",
                    description=f"{name} has committed fraud {len(frauds)} times recently. Clients keep hiring them — either the protocol isn't surfacing this, or no one is checking.",
                    agents_involved=[agent_id],
                    day=day, phase=phase, severity="critical",
                    evidence={"fraud_count": len(frauds)},
                ))
        return events

    def _check_bankruptcy_risk(self, agents: dict, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("bankruptcy", 0) > phase - 3:
            return []
        self._last_check_phase["bankruptcy"] = phase

        events = []
        for agent_id, agent in agents.items():
            if agent.is_bankrupt:
                continue
            if agent.capital < agent.maintenance_cost * 5:
                events.append(NarrativeEvent(
                    event_type="bankruptcy_risk",
                    title=f"{agent.name} is in financial peril",
                    description=f"{agent.name} has only {agent.capital:.0f} coins — less than 5 days of operating costs. They are desperate for work and may accept any price.",
                    agents_involved=[agent_id],
                    day=day, phase=phase, severity="warning",
                    evidence={"capital": agent.capital, "daily_cost": agent.maintenance_cost},
                ))
        return events

    def _check_price_gouging(self, agents: dict, contracts: List, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("gouging", 0) > phase - 15:
            return []
        self._last_check_phase["gouging"] = phase

        if len(contracts) < 5:
            return []

        recent = contracts[-20:]
        prices = [c.agreed_price for c in recent]
        if len(prices) < 5:
            return []

        avg = statistics.mean(prices)
        stdev = statistics.stdev(prices) if len(prices) > 1 else 0

        events = []
        agent_prices = defaultdict(list)
        for c in recent:
            agent_prices[c.agent_id].append(c.agreed_price)

        for agent_id, ap in agent_prices.items():
            if len(ap) >= 3:
                agent_avg = statistics.mean(ap)
                if agent_avg > avg + 1.5 * stdev and stdev > 0:
                    agent = agents.get(agent_id)
                    name = agent.name if agent else agent_id
                    events.append(NarrativeEvent(
                        event_type="price_gouging",
                        title=f"{name} is charging well above market",
                        description=f"{name}'s average price is {agent_avg:.0f} — far above the market average of {avg:.0f}. Either they're highly trusted or exploiting a niche.",
                        agents_involved=[agent_id],
                        day=day, phase=phase, severity="info",
                        evidence={"agent_avg": agent_avg, "market_avg": avg},
                    ))
        return events

    def _check_trust_collapse(self, agents: dict, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("trust", 0) > phase - 9:
            return []
        self._last_check_phase["trust"] = phase

        events = []
        for agent_id, agent in agents.items():
            rels = agent.memory.relationships.values()
            bad = [r for r in rels if r.trust_score < 0.2 and r.interaction_count > 2]
            if len(bad) >= 3:
                events.append(NarrativeEvent(
                    event_type="trust_collapse",
                    title=f"{agent.name}'s network is collapsing",
                    description=f"{agent.name} has burned trust with {len(bad)} partners. Their network is fragmenting — fewer agents will work with them.",
                    agents_involved=[agent_id],
                    day=day, phase=phase, severity="warning",
                    evidence={"burned_relationships": len(bad)},
                ))
        return events

    def _check_quality_race(self, agents: dict, contracts: List, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("quality_race", 0) > phase - 18:
            return []
        self._last_check_phase["quality_race"] = phase

        from marketplace.models import ContractStatus
        recent = [c for c in contracts[-30:] if c.true_quality is not None]
        if len(recent) < 6:
            return []

        qualities = [c.true_quality for c in recent]
        avg_q = statistics.mean(qualities)

        events = []
        if avg_q < 0.3:
            events.append(NarrativeEvent(
                event_type="race_to_bottom",
                title="Quality is collapsing across the market",
                description=f"Average delivery quality has fallen to {avg_q:.0%}. The market is in a race to the bottom — agents are cutting corners with little consequence.",
                agents_involved=[],
                day=day, phase=phase, severity="critical",
                evidence={"avg_quality": avg_q},
            ))
        elif avg_q > 0.75:
            events.append(NarrativeEvent(
                event_type="quality_flourishing",
                title="Market quality is at a historic high",
                description=f"Average delivery quality is {avg_q:.0%}. The current protocol is creating strong incentives for excellence.",
                agents_involved=[],
                day=day, phase=phase, severity="info",
                evidence={"avg_quality": avg_q},
            ))
        return events

    def _check_communication_patterns(self, agents: dict, messages: List, phase: int, day: int) -> List[NarrativeEvent]:
        if self._last_check_phase.get("comms", 0) > phase - 12:
            return []
        self._last_check_phase["comms"] = phase

        events = []
        from communication.channels import MessageChannel

        # Check for heavy private communication between specific agents (coordination?)
        pair_counts = defaultdict(int)
        for m in messages[-50:]:
            if m.channel == MessageChannel.PRIVATE:
                pair = tuple(sorted([m.sender_id, m.recipient_id or "?"]))
                pair_counts[pair] += 1

        for pair, count in pair_counts.items():
            if count >= 8 and "system" not in pair and "?" not in pair:
                names = [agents[p].name if p in agents else p for p in pair]
                events.append(NarrativeEvent(
                    event_type="private_coordination",
                    title=f"{names[0]} and {names[1]} are coordinating intensely",
                    description=f"These two have exchanged {count} private messages recently. This level of private communication suggests active coordination — possibly legitimate alliance or collusion.",
                    agents_involved=list(pair),
                    day=day, phase=phase, severity="info",
                    evidence={"message_count": count},
                ))
        return events

    def get_recent_events(self, n: int = 10) -> List[NarrativeEvent]:
        return self._events[-n:]

    def get_all_events(self) -> List[NarrativeEvent]:
        return list(self._events)

    def get_events_by_type(self, event_type: str) -> List[NarrativeEvent]:
        return [e for e in self._events if e.event_type == event_type]
