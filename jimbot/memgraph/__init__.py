"""Memgraph knowledge graph subsystem for JimBot.

This package provides high-performance graph database functionality for:
- Joker synergy calculations
- Strategy pattern recognition
- Card relationship analysis
- Victory path optimization
"""

from .client import MemgraphClient
from .query_builder import QueryBuilder
from .feature_extractor import GraphFeatureExtractor

__all__ = [
    "MemgraphClient",
    "QueryBuilder",
    "GraphFeatureExtractor",
]

__version__ = "0.1.0"
