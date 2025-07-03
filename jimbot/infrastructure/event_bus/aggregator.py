"""Event Aggregator Module

Aggregates high-frequency events into summary events.
"""

from collections import defaultdict
from typing import List

from .event_bus import Event


class EventAggregator:
    """Aggregates multiple events into summary events"""

    def __init__(self):
        self.aggregation_rules = {}
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default aggregation rules"""
        self.aggregation_rules.update(
            {
                "game.card.played": self._aggregate_cards_played,
                "game.damage.dealt": self._aggregate_damage,
                "game.money.earned": self._aggregate_money,
                "game.score.earned": self._aggregate_score,
            }
        )

    async def aggregate(self, events: List[Event]) -> List[Event]:
        """Aggregate events based on type"""
        grouped = defaultdict(list)
        for event in events:
            grouped[event.topic].append(event)

        aggregated = []
        for topic, group in grouped.items():
            if topic in self.aggregation_rules:
                result = self.aggregation_rules[topic](group)
                if result:
                    aggregated.append(result)
            else:
                aggregated.extend(group)

        return aggregated
