"""
MCP (Model-Context-Protocol) subsystem for JimBot.

This package provides real-time communication between the BalatroMCP mod
and the JimBot learning system, with <100ms event aggregation latency.
"""

from jimbot.mcp.server import MCPServer
from jimbot.mcp.client import MCPClient
from jimbot.mcp.aggregator import EventAggregator

__version__ = "0.1.0"
__all__ = ["MCPServer", "MCPClient", "EventAggregator"]