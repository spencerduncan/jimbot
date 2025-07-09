"""
MCP WebSocket server implementation.

This module provides the main WebSocket server that receives events from
the BalatroMCP mod and forwards them to the event aggregator.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from jimbot.mcp.aggregator import EventAggregator
from jimbot.mcp.utils import MetricsCollector, validate_event, check_rate_limit, get_validation_errors

logger = logging.getLogger(__name__)


class MCPServer:
    """
    WebSocket server for receiving game events from BalatroMCP mod.

    Attributes:
        host: Server host address
        port: Server port number
        aggregator: Event aggregator instance
        clients: Set of connected WebSocket clients
        metrics: Performance metrics collector
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Initialize MCP server.

        Args:
            host: Host address to bind to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.aggregator = EventAggregator()
        self.clients: Set[WebSocketServerProtocol] = set()
        self.metrics = MetricsCollector()
        self._server = None

    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting MCP server on {self.host}:{self.port}")

        # Start event aggregator
        await self.aggregator.start()

        # Start WebSocket server
        self._server = await websockets.serve(
            self.handle_client, self.host, self.port, ping_interval=30, ping_timeout=10
        )

        logger.info("MCP server started successfully")

    async def stop(self):
        """Stop the WebSocket server."""
        logger.info("Stopping MCP server...")

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients], return_exceptions=True
            )

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Stop aggregator
        await self.aggregator.stop()

        logger.info("MCP server stopped")

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle individual WebSocket client connection.

        Args:
            websocket: WebSocket connection
            path: Request path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_id}")

        # Add to active clients
        self.clients.add(websocket)
        self.metrics.gauge("websocket_connections", len(self.clients))

        try:
            async for message in websocket:
                await self._process_message(message, client_id)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Remove from active clients
            self.clients.discard(websocket)
            self.metrics.gauge("websocket_connections", len(self.clients))

    async def _process_message(self, message: str, client_id: str):
        """
        Process incoming message from client.

        Args:
            message: Raw message string
            client_id: Client identifier
        """
        start_time = time.time()

        try:
            # Parse JSON message
            data = json.loads(message)

            # Validate event structure
            if not validate_event(data, client_id):
                logger.warning(f"Invalid event from {client_id}: {data}")
                self.metrics.increment("invalid_events_total")
                return

            # Sanitize event data to prevent injection attacks
            data = sanitize_event_data(data)

            # Add metadata
            data["_client_id"] = client_id
            data["_received_at"] = start_time

            # Send to aggregator
            await self.aggregator.add_event(data)

            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.histogram("message_processing_ms", processing_time)
            self.metrics.increment("events_processed_total")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {client_id}: {e}")
            self.metrics.increment("invalid_messages_total")
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            self.metrics.increment("processing_errors_total")


async def main():
    """Main entry point for MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP WebSocket Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start server
    server = MCPServer(host=args.host, port=args.port)

    try:
        await server.start()
        # Keep server running
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
