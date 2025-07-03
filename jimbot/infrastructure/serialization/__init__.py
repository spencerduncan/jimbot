"""Serialization Module

Protocol Buffer schemas and serialization utilities.
"""

from .schema_registry import SchemaRegistry
from .serializer import ProtobufSerializer

__all__ = ["ProtobufSerializer", "SchemaRegistry"]
