"""Serialization Module

Protocol Buffer schemas and serialization utilities.
"""

from .serializer import ProtobufSerializer
from .schema_registry import SchemaRegistry

__all__ = ['ProtobufSerializer', 'SchemaRegistry']