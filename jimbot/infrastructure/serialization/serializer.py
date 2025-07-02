"""Protocol Buffer Serializer

Handles serialization/deserialization of events.
"""

from typing import Any, Type
import logging

logger = logging.getLogger(__name__)


class ProtobufSerializer:
    """Serializes/deserializes Protocol Buffer messages"""
    
    def __init__(self):
        self.message_types = {}
        
    def register_type(self, message_type: Type, type_name: str):
        """Register a Protocol Buffer message type"""
        self.message_types[type_name] = message_type
        
    def serialize(self, message: Any) -> bytes:
        """Serialize message to bytes"""
        if hasattr(message, 'SerializeToString'):
            return message.SerializeToString()
        else:
            # Fallback for non-protobuf messages
            import json
            return json.dumps(message).encode('utf-8')
            
    def deserialize(self, data: bytes, type_name: str) -> Any:
        """Deserialize bytes to message"""
        if type_name in self.message_types:
            message = self.message_types[type_name]()
            message.ParseFromString(data)
            return message
        else:
            # Fallback
            import json
            return json.loads(data.decode('utf-8'))