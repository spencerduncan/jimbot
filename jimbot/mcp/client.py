"""
MCP client implementation for testing and integration.

This module provides a WebSocket client for connecting to the MCP server
and sending test events. Useful for development and testing.
"""

import asyncio
import json
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)


class MCPClient:
    """
    WebSocket client for MCP server communication.

    Attributes:
        url: WebSocket server URL
        websocket: Active WebSocket connection
    """

    def __init__(self, url: str = "ws://localhost:8765/events"):
        """
        Initialize MCP client.

        Args:
            url: WebSocket server URL
        """
        self.url = url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self):
        """Connect to the MCP server."""
        logger.info(f"Connecting to MCP server at {self.url}")
        self.websocket = await websockets.connect(self.url)
        logger.info("Connected successfully")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from MCP server")

    async def send_event(self, event: Dict):
        """
        Send an event to the MCP server.

        Args:
            event: Event data dictionary
        """
        if not self.websocket:
            raise RuntimeError("Not connected to MCP server")

        # Ensure timestamp
        if "timestamp" not in event:
            event["timestamp"] = time.time()

        # Send as JSON
        message = json.dumps(event)
        await self.websocket.send(message)
        logger.debug(f"Sent event: {event['type']}")

    @asynccontextmanager
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class MockEventGenerator:
    """Generate mock Balatro game events for testing."""

    def __init__(self, game_id: str = None):
        """
        Initialize mock event generator.

        Args:
            game_id: Game session ID (generated if not provided)
        """
        self.game_id = game_id or f"mock_{int(time.time())}"
        self.round = 1
        self.money = 4
        self.hands_played = 0

    def generate_game_start(self) -> Dict:
        """Generate game start event."""
        return {
            "type": "game_start",
            "timestamp": time.time(),
            "game_id": self.game_id,
            "data": {
                "seed": random.randint(1000000, 9999999),
                "stake": "white",
                "deck": "red",
                "starting_money": self.money,
            },
        }

    def generate_hand_played(self) -> Dict:
        """Generate hand played event."""
        hand_types = [
            "pair",
            "two_pair",
            "three_of_a_kind",
            "straight",
            "flush",
            "full_house",
            "four_of_a_kind",
            "straight_flush",
        ]

        hand_type = random.choice(hand_types)
        base_scores = {
            "pair": 10,
            "two_pair": 20,
            "three_of_a_kind": 30,
            "straight": 30,
            "flush": 35,
            "full_house": 40,
            "four_of_a_kind": 60,
            "straight_flush": 100,
        }

        score = base_scores[hand_type] * random.randint(1, 5)
        self.hands_played += 1

        return {
            "type": "hand_played",
            "timestamp": time.time(),
            "game_id": self.game_id,
            "data": {
                "hand_type": hand_type,
                "cards": self._generate_cards(5),
                "score": score,
                "multiplier": random.randint(1, 5),
                "hands_remaining": 4 - (self.hands_played % 4),
            },
        }

    def generate_shop_entered(self) -> Dict:
        """Generate shop entered event."""
        self.round += 1
        self.money += random.randint(5, 20)

        return {
            "type": "shop_entered",
            "timestamp": time.time(),
            "game_id": self.game_id,
            "data": {
                "round": self.round,
                "money": self.money,
                "available_items": self._generate_shop_items(),
            },
        }

    def generate_card_purchased(self) -> Dict:
        """Generate card purchased event."""
        items = ["joker", "planet", "tarot", "spectral"]
        item_type = random.choice(items)
        cost = random.randint(3, 8)
        self.money -= cost

        return {
            "type": "card_purchased",
            "timestamp": time.time(),
            "game_id": self.game_id,
            "data": {
                "card_type": item_type,
                "card_id": f"{item_type}_{random.randint(1, 20)}",
                "cost": cost,
                "money_remaining": self.money,
            },
        }

    def generate_game_over(self) -> Dict:
        """Generate game over event."""
        return {
            "type": "game_over",
            "timestamp": time.time(),
            "game_id": self.game_id,
            "data": {
                "final_score": random.randint(1000, 50000),
                "round_reached": self.round,
                "reason": random.choice(["blind_failed", "boss_defeated"]),
            },
        }

    def _generate_cards(self, count: int) -> List[str]:
        """Generate random playing cards."""
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        suits = ["H", "D", "C", "S"]
        cards = []

        for _ in range(count):
            card = f"{random.choice(ranks)}{random.choice(suits)}"
            cards.append(card)

        return cards

    def _generate_shop_items(self) -> List[Dict]:
        """Generate random shop items."""
        items = []
        for _ in range(random.randint(2, 6)):
            item_type = random.choice(["joker", "planet", "tarot", "spectral"])
            items.append(
                {
                    "type": item_type,
                    "id": f"{item_type}_{random.randint(1, 20)}",
                    "cost": random.randint(3, 8),
                    "name": f"Mock {item_type.capitalize()}",
                }
            )
        return items


async def test_connection(url: str = "ws://localhost:8765/events"):
    """Test connection to MCP server."""
    async with MCPClient(url) as client:
        # Send test event
        test_event = {
            "type": "test",
            "timestamp": time.time(),
            "game_id": "test_connection",
            "data": {"message": "Hello from MCP client"},
        }
        await client.send_event(test_event)
        logger.info("Test event sent successfully")


async def send_mock_events(
    url: str = "ws://localhost:8765/events", rate: int = 10, duration: int = 60
):
    """
    Send mock events at specified rate.

    Args:
        url: MCP server URL
        rate: Events per second
        duration: Duration in seconds
    """
    async with MCPClient(url) as client:
        generator = MockEventGenerator()

        # Send game start
        await client.send_event(generator.generate_game_start())

        start_time = time.time()
        event_count = 0

        while time.time() - start_time < duration:
            # Generate random event
            event_type = random.choices(
                ["hand_played", "shop_entered", "card_purchased"], weights=[70, 20, 10]
            )[0]

            if event_type == "hand_played":
                event = generator.generate_hand_played()
            elif event_type == "shop_entered":
                event = generator.generate_shop_entered()
            else:
                event = generator.generate_card_purchased()

            await client.send_event(event)
            event_count += 1

            # Control rate
            await asyncio.sleep(1.0 / rate)

        # Send game over
        await client.send_event(generator.generate_game_over())

        logger.info(f"Sent {event_count} events in {duration} seconds")


async def main():
    """Main entry point for MCP client."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP WebSocket Client")
    parser.add_argument(
        "--url", default="ws://localhost:8765/events", help="MCP server URL"
    )
    parser.add_argument(
        "--test-connection", action="store_true", help="Test connection and exit"
    )
    parser.add_argument("--mock-events", action="store_true", help="Send mock events")
    parser.add_argument(
        "--rate", type=int, default=10, help="Events per second for mock mode"
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Duration in seconds for mock mode"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.test_connection:
        await test_connection(args.url)
    elif args.mock_events:
        await send_mock_events(args.url, args.rate, args.duration)
    else:
        logger.error("Please specify --test-connection or --mock-events")


if __name__ == "__main__":
    asyncio.run(main())
