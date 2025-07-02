"""
Integration tests for MCP to Ray communication.

Tests the full flow from game events to training updates.
"""

import asyncio
import json
import time
import websockets
import pytest
import ray
from unittest.mock import patch

from jimbot.mcp.server import MCPServer
from jimbot.mcp.aggregator import EventAggregator
from jimbot.training.environment import BalatroEnv


@pytest.mark.integration
@pytest.mark.requires_docker
class TestMCPToRayIntegration:
    """Test integration between MCP and Ray components."""
    
    @pytest.fixture(scope="class")
    def ray_cluster(self):
        """Initialize Ray cluster for testing."""
        ray.init(ignore_reinit_error=True)
        yield
        ray.shutdown()
    
    @pytest.fixture
    async def mcp_server(self):
        """Start MCP server for testing."""
        server = MCPServer(host="localhost", port=8899)
        task = asyncio.create_task(server.start())
        await asyncio.sleep(1)  # Let server start
        yield server
        server.stop()
        await task
    
    @pytest.mark.asyncio
    async def test_event_flow_to_training(self, mcp_server, ray_cluster):
        """Test that game events flow from MCP to Ray training."""
        # Create Ray environment
        env = BalatroEnv.remote()
        
        # Connect to MCP server
        async with websockets.connect("ws://localhost:8899") as websocket:
            # Send game state event
            game_state = {
                "type": "game_state",
                "timestamp": time.time(),
                "data": {
                    "ante": 3,
                    "money": 45,
                    "jokers": ["Joker", "Baseball Card"],
                    "hand": ["AH", "KH", "QH", "JH", "10H", "9H", "8H", "7H"],
                    "blinds_defeated": 15
                }
            }
            
            await websocket.send(json.dumps(game_state))
            
            # Wait for aggregation
            await asyncio.sleep(0.2)
            
            # Verify event was processed
            response = await websocket.recv()
            resp_data = json.loads(response)
            
            assert resp_data["type"] == "ack"
            assert resp_data["event_id"] == game_state.get("id")
        
        # Verify Ray environment received update
        state = ray.get(env.get_state.remote())
        assert state["ante"] == 3
        assert len(state["jokers"]) == 2
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, mcp_server):
        """Test that event batching meets performance requirements."""
        events_sent = 0
        events_received = 0
        
        async with websockets.connect("ws://localhost:8899") as websocket:
            # Send burst of events
            start_time = time.time()
            
            for i in range(100):
                event = {
                    "type": "action",
                    "timestamp": time.time(),
                    "data": {
                        "action": "play_hand",
                        "cards": [0, 1, 2, 3, 4]
                    }
                }
                await websocket.send(json.dumps(event))
                events_sent += 1
            
            # Receive acknowledgments
            while events_received < events_sent:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if json.loads(response)["type"] == "batch_ack":
                    events_received += json.loads(response)["count"]
            
            elapsed = time.time() - start_time
        
        # Verify performance
        assert events_received == events_sent
        assert elapsed < 1.0  # Should process 100 events in under 1 second
        
        # Check batching efficiency
        aggregator_stats = mcp_server.get_aggregator_stats()
        assert aggregator_stats["batches_processed"] < 10  # Should batch efficiently
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, mcp_server, ray_cluster):
        """Test system recovery from component failures."""
        env = BalatroEnv.remote()
        
        async with websockets.connect("ws://localhost:8899") as websocket:
            # Send valid event
            await websocket.send(json.dumps({
                "type": "game_state",
                "data": {"ante": 1}
            }))
            
            # Send invalid event
            await websocket.send("invalid json")
            
            # Send another valid event
            await websocket.send(json.dumps({
                "type": "game_state",
                "data": {"ante": 2}
            }))
            
            # System should recover and process valid events
            responses = []
            for _ in range(2):
                response = await websocket.recv()
                responses.append(json.loads(response))
            
            # Should have 2 acknowledgments (invalid event rejected)
            assert len([r for r in responses if r["type"] == "ack"]) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, mcp_server):
        """Test MCP handles multiple concurrent WebSocket connections."""
        connections = []
        
        # Create multiple connections
        for i in range(10):
            ws = await websockets.connect("ws://localhost:8899")
            connections.append(ws)
        
        # Send events from all connections
        tasks = []
        for i, ws in enumerate(connections):
            event = {
                "type": "test",
                "connection_id": i,
                "timestamp": time.time()
            }
            tasks.append(ws.send(json.dumps(event)))
        
        await asyncio.gather(*tasks)
        
        # Verify all connections receive responses
        responses = []
        for ws in connections:
            response = await ws.recv()
            responses.append(json.loads(response))
        
        # Clean up
        for ws in connections:
            await ws.close()
        
        assert len(responses) == 10
        assert all(r["type"] == "ack" for r in responses)
    
    def test_ray_environment_reset(self, ray_cluster):
        """Test Ray environment reset and state management."""
        env = BalatroEnv.remote()
        
        # Reset environment
        initial_state = ray.get(env.reset.remote())
        assert initial_state is not None
        
        # Take some actions
        for _ in range(5):
            action = 0  # Simple action
            state, reward, done, info = ray.get(env.step.remote(action))
        
        # Reset again
        reset_state = ray.get(env.reset.remote())
        
        # Verify reset brings environment to initial state
        assert reset_state.shape == initial_state.shape
        game_state = ray.get(env.get_state.remote())
        assert game_state["ante"] == 1
        assert game_state["money"] == 10  # Starting money