"""Protocol Buffer Serializer

Handles serialization/deserialization of events with JSON compatibility.
"""

from typing import Any, Type, Optional
import logging
import json
from enum import Enum

from .json_compatibility import JsonCompatibilityLayer

logger = logging.getLogger(__name__)


class SerializationFormat(str, Enum):
    """Supported serialization formats"""

    PROTOBUF = "protobuf"
    JSON = "json"
    JSON_COMPAT = "json_compat"  # JSON with protobuf compatibility


class ProtobufSerializer:
    """Serializes/deserializes Protocol Buffer messages with JSON compatibility"""

    def __init__(self):
        self.message_types = {}
        self.json_compat = JsonCompatibilityLayer()
        self.default_format = SerializationFormat.PROTOBUF
        self._register_default_types()

    def _register_default_types(self):
        """Register default Protocol Buffer message types"""
        try:
            # Import generated protobuf classes
            from jimbot.proto import balatro_events_pb2

            # Register event types
            self.register_type(balatro_events_pb2.Event, "Event")
            self.register_type(balatro_events_pb2.EventBatch, "EventBatch")
            self.register_type(balatro_events_pb2.GameStateEvent, "GameStateEvent")
            self.register_type(
                balatro_events_pb2.LearningDecisionRequest, "LearningDecisionRequest"
            )
            self.register_type(
                balatro_events_pb2.LearningDecisionResponse, "LearningDecisionResponse"
            )

            logger.info("Registered default protobuf types")
        except ImportError:
            logger.warning("Protobuf types not generated yet. Run protoc to generate.")

    def register_type(self, message_type: Type, type_name: str):
        """Register a Protocol Buffer message type"""
        self.message_types[type_name] = message_type
        logger.debug(f"Registered protobuf type: {type_name}")

    def serialize(
        self, message: Any, format: Optional[SerializationFormat] = None
    ) -> bytes:
        """Serialize message to bytes

        Args:
            message: Message to serialize (protobuf Message or dict)
            format: Serialization format to use

        Returns:
            Serialized bytes
        """
        format = format or self.default_format

        try:
            if format == SerializationFormat.PROTOBUF:
                if hasattr(message, "SerializeToString"):
                    return message.SerializeToString()
                else:
                    # Convert dict to protobuf first
                    proto_msg = self.json_compat.json_to_proto(message)
                    if proto_msg:
                        return proto_msg.SerializeToString()
                    else:
                        raise ValueError("Failed to convert to protobuf")

            elif format == SerializationFormat.JSON:
                if isinstance(message, dict):
                    return json.dumps(message).encode("utf-8")
                else:
                    # Convert protobuf to JSON
                    json_msg = self.json_compat.proto_to_json(message)
                    if json_msg:
                        return json.dumps(json_msg).encode("utf-8")
                    else:
                        raise ValueError("Failed to convert to JSON")

            elif format == SerializationFormat.JSON_COMPAT:
                # Ensure JSON compatibility while preserving protobuf structure
                if hasattr(message, "SerializeToString"):
                    json_msg = self.json_compat.proto_to_json(message)
                else:
                    json_msg = message

                return json.dumps(json_msg, ensure_ascii=False).encode("utf-8")

            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Serialization failed: {e}", exc_info=True)
            raise

    def deserialize(
        self, data: bytes, type_name: str, format: Optional[SerializationFormat] = None
    ) -> Any:
        """Deserialize bytes to message

        Args:
            data: Serialized bytes
            type_name: Type name of the message
            format: Serialization format of the data

        Returns:
            Deserialized message
        """
        format = format or self.default_format

        try:
            if format == SerializationFormat.PROTOBUF:
                if type_name in self.message_types:
                    message = self.message_types[type_name]()
                    message.ParseFromString(data)
                    return message
                else:
                    raise ValueError(f"Unknown type: {type_name}")

            elif format == SerializationFormat.JSON:
                json_data = json.loads(data.decode("utf-8"))

                # If requesting protobuf type, convert
                if type_name in self.message_types:
                    return self.json_compat.json_to_proto(json_data)
                else:
                    return json_data

            elif format == SerializationFormat.JSON_COMPAT:
                json_data = json.loads(data.decode("utf-8"))

                # Always try to convert to protobuf for compatibility
                proto_msg = self.json_compat.json_to_proto(json_data)
                if proto_msg and type_name in self.message_types:
                    return proto_msg
                else:
                    return json_data

            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Deserialization failed: {e}", exc_info=True)
            raise

    def convert_format(
        self,
        message: Any,
        from_format: SerializationFormat,
        to_format: SerializationFormat,
    ) -> Any:
        """Convert message between formats

        Args:
            message: Message to convert
            from_format: Current format of the message
            to_format: Target format

        Returns:
            Message in target format
        """
        if from_format == to_format:
            return message

        # Serialize to bytes in source format
        data = self.serialize(message, from_format)

        # Determine type for deserialization
        if hasattr(message, "__class__"):
            type_name = message.__class__.__name__
        else:
            type_name = "Event"  # Default to Event type

        # Deserialize in target format
        return self.deserialize(data, type_name, to_format)

    def get_registered_types(self) -> list:
        """Get list of registered type names"""
        return list(self.message_types.keys())

    def set_default_format(self, format: SerializationFormat):
        """Set default serialization format"""
        self.default_format = format
        logger.info(f"Set default serialization format to: {format}")

    def set_json_compatibility_mode(
        self, strict: bool = False, preserve_unknown: bool = True
    ):
        """Configure JSON compatibility layer

        Args:
            strict: Fail on unknown fields if True
            preserve_unknown: Preserve unknown fields in metadata
        """
        self.json_compat.strict_mode = strict
        self.json_compat.preserve_unknown = preserve_unknown
