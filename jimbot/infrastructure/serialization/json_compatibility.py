"""JSON Compatibility Layer for Protocol Buffers

Provides bidirectional conversion between JSON events and Protocol Buffer events
to maintain backward compatibility with existing BalatroMCP JSON format.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union

from google.protobuf import json_format, struct_pb2
from google.protobuf.message import Message

# Import generated protobuf classes (these will be generated by protoc)
# from jimbot.proto import balatro_events_pb2
# from jimbot.proto import json_compatibility_pb2

logger = logging.getLogger(__name__)


class JsonCompatibilityLayer:
    """Handles conversion between JSON and Protocol Buffer formats"""

    def __init__(self):
        """Initialize the compatibility layer"""
        self.type_mappings = self._initialize_type_mappings()
        self.field_mappings = self._initialize_field_mappings()
        self.strict_mode = False
        self.preserve_unknown = True

    def _initialize_type_mappings(self) -> Dict[str, str]:
        """Initialize JSON type to protobuf type mappings"""
        return {
            # Game flow events
            "GAME_STATE": "EVENT_TYPE_GAME_STATE",
            "game_state": "EVENT_TYPE_GAME_STATE",
            "HEARTBEAT": "EVENT_TYPE_HEARTBEAT",
            "heartbeat": "EVENT_TYPE_HEARTBEAT",
            "game_start": "EVENT_TYPE_GAME_START",
            "game_over": "EVENT_TYPE_GAME_OVER",
            "game_end": "EVENT_TYPE_GAME_OVER",
            # Money and score events
            "money_changed": "EVENT_TYPE_MONEY_CHANGED",
            "score_changed": "EVENT_TYPE_SCORE_CHANGED",
            # Hand events
            "hand_played": "EVENT_TYPE_HAND_PLAYED",
            "hand": "EVENT_TYPE_HAND_PLAYED",
            "cards_discarded": "EVENT_TYPE_CARDS_DISCARDED",
            "discard": "EVENT_TYPE_CARDS_DISCARDED",
            # Joker events
            "jokers_changed": "EVENT_TYPE_JOKERS_CHANGED",
            "joker_triggered": "EVENT_TYPE_JOKER_TRIGGERED",
            "joker": "EVENT_TYPE_JOKER_TRIGGERED",
            # Round and phase events
            "round_changed": "EVENT_TYPE_ROUND_CHANGED",
            "round_start": "EVENT_TYPE_ROUND_CHANGED",
            "round_started": "EVENT_TYPE_ROUND_CHANGED",
            "phase_changed": "EVENT_TYPE_PHASE_CHANGED",
            "round_complete": "EVENT_TYPE_ROUND_COMPLETE",
            "round_end": "EVENT_TYPE_ROUND_COMPLETE",
            "round_ended": "EVENT_TYPE_ROUND_COMPLETE",
            # Shop events
            "shop_entered": "EVENT_TYPE_SHOP_ENTERED",
            "shop": "EVENT_TYPE_SHOP_ENTERED",
            "card_purchased": "EVENT_TYPE_CARD_PURCHASED",
            "purchase": "EVENT_TYPE_CARD_PURCHASED",
            "card_sold": "EVENT_TYPE_CARD_SOLD",
            "sell": "EVENT_TYPE_CARD_SOLD",
            # Other game events
            "blind_defeated": "EVENT_TYPE_BLIND_DEFEATED",
            "blind": "EVENT_TYPE_BLIND_DEFEATED",
            "card_enhanced": "EVENT_TYPE_CARD_ENHANCED",
            "enhance": "EVENT_TYPE_CARD_ENHANCED",
            "state_snapshot": "EVENT_TYPE_STATE_SNAPSHOT",
            "snapshot": "EVENT_TYPE_STATE_SNAPSHOT",
            # System events
            "connection_test": "EVENT_TYPE_CONNECTION_TEST",
            "ERROR": "EVENT_TYPE_ERROR",
            "error": "EVENT_TYPE_ERROR",
            # Learning/Strategy events
            "LEARNING_DECISION": "EVENT_TYPE_LEARNING_DECISION_REQUEST",
            "learning_decision_request": "EVENT_TYPE_LEARNING_DECISION_REQUEST",
            "learning_decision_response": "EVENT_TYPE_LEARNING_DECISION_RESPONSE",
            "strategy_request": "EVENT_TYPE_STRATEGY_REQUEST",
            "strategy_response": "EVENT_TYPE_STRATEGY_RESPONSE",
            # Knowledge/Metrics events
            "knowledge_update": "EVENT_TYPE_KNOWLEDGE_UPDATE",
            "metric": "EVENT_TYPE_METRIC",
        }

    def _initialize_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """Initialize field mappings for each event type"""
        return {
            "EVENT_TYPE_GAME_STATE": {
                "payload.game_state": "game_state",
                "payload.in_game": "game_state.in_game",
                "payload.game_id": "game_state.game_id",
                "payload.ante": "game_state.ante",
                "payload.round": "game_state.round",
                "payload.money": "game_state.money",
                "payload.jokers": "game_state.jokers",
                "payload.hand": "game_state.hand",
                "payload.deck": "game_state.deck",
            },
            "EVENT_TYPE_LEARNING_DECISION_REQUEST": {
                "payload.request_id": "learning_decision_request.request_id",
                "payload.game_state": "learning_decision_request.game_state",
                "payload.available_actions": "learning_decision_request.available_actions",
                "payload.time_limit_ms": "learning_decision_request.time_limit_ms",
            },
        }

    def json_to_proto(self, json_event: Dict[str, Any]) -> Optional[Message]:
        """Convert JSON event to Protocol Buffer event

        Args:
            json_event: JSON event dictionary

        Returns:
            Protocol Buffer Event message or None if conversion fails
        """
        try:
            # Import here to avoid circular imports
            from jimbot.proto import balatro_events_pb2

            # Create base event
            proto_event = balatro_events_pb2.Event()

            # Map basic fields
            proto_event.event_id = json_event.get("event_id", self._generate_event_id())
            proto_event.timestamp = json_event.get(
                "timestamp", int(datetime.now().timestamp() * 1000)
            )
            proto_event.source = json_event.get("source", "unknown")
            proto_event.version = json_event.get("version", 1)
            proto_event.priority = json_event.get("priority", "normal")
            proto_event.game_id = json_event.get("game_id", "")
            proto_event.session_id = json_event.get("session_id", "")
            proto_event.sequence_number = json_event.get("sequence_number", 0)

            # Map event type
            json_type = json_event.get("type", "unknown")
            proto_type_name = self.type_mappings.get(json_type, "EVENT_TYPE_CUSTOM")
            proto_event.type = getattr(balatro_events_pb2.EventType, proto_type_name)

            # Map payload based on event type
            if proto_type_name != "EVENT_TYPE_CUSTOM":
                self._map_payload(json_event, proto_event, proto_type_name)
            else:
                # For unknown types, store in custom_event
                proto_event.custom_event.Pack(
                    self._json_to_any(json_event.get("payload", {}))
                )

            # Map metadata
            metadata = json_event.get("metadata", {})
            for key, value in metadata.items():
                proto_event.metadata[key] = str(value)

            # Preserve unknown fields if configured
            if self.preserve_unknown:
                unknown_fields = self._extract_unknown_fields(json_event)
                for key, value in unknown_fields.items():
                    proto_event.metadata[f"json_{key}"] = json.dumps(value)

            return proto_event

        except Exception as e:
            logger.error(f"Failed to convert JSON to proto: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return None

    def proto_to_json(self, proto_event: Message) -> Optional[Dict[str, Any]]:
        """Convert Protocol Buffer event to JSON event

        Args:
            proto_event: Protocol Buffer Event message

        Returns:
            JSON event dictionary or None if conversion fails
        """
        try:
            # Use protobuf's built-in JSON conversion with custom handling
            json_dict = json_format.MessageToDict(
                proto_event,
                preserving_proto_field_name=True,
                including_default_value_fields=False,
            )

            # Remap to match legacy JSON format
            json_event = {
                "type": self._proto_type_to_json(proto_event.type),
                "source": proto_event.source,
                "timestamp": proto_event.timestamp,
                "event_id": proto_event.event_id,
                "priority": proto_event.priority or "normal",
            }

            # Add optional fields if present
            if proto_event.game_id:
                json_event["game_id"] = proto_event.game_id
            if proto_event.session_id:
                json_event["session_id"] = proto_event.session_id

            # Extract payload
            payload_field = proto_event.WhichOneof("payload")
            if payload_field:
                payload_data = getattr(proto_event, payload_field)
                json_event["payload"] = json_format.MessageToDict(
                    payload_data, preserving_proto_field_name=True
                )

                # Apply any necessary field transformations
                self._transform_payload_fields(json_event, proto_event.type)

            # Add metadata
            if proto_event.metadata:
                json_event["metadata"] = dict(proto_event.metadata)

                # Extract any preserved JSON fields
                for key, value in proto_event.metadata.items():
                    if key.startswith("json_"):
                        try:
                            json_event[key[5:]] = json.loads(value)
                        except:
                            pass

            return json_event

        except Exception as e:
            logger.error(f"Failed to convert proto to JSON: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return None

    def _map_payload(
        self, json_event: Dict[str, Any], proto_event: Message, proto_type: str
    ):
        """Map JSON payload to protobuf payload based on event type"""
        from jimbot.proto import balatro_events_pb2

        payload = json_event.get("payload", {})

        # Map based on event type
        if proto_type == "EVENT_TYPE_GAME_STATE":
            game_state = proto_event.game_state
            self._map_game_state(payload, game_state)

        elif proto_type == "EVENT_TYPE_LEARNING_DECISION_REQUEST":
            request = proto_event.learning_decision_request
            request.request_id = payload.get("request_id", "")
            request.time_limit_ms = payload.get("time_limit_ms", 1000)

            # Map game state if present
            if "game_state" in payload:
                self._map_game_state(payload["game_state"], request.game_state)

            # Map available actions
            for action_data in payload.get("available_actions", []):
                action = request.available_actions.add()
                self._map_action(action_data, action)

        elif proto_type == "EVENT_TYPE_ERROR":
            error = proto_event.error
            error.error_code = payload.get("error_code", "UNKNOWN")
            error.message = payload.get("message", "")
            error.stack_trace = payload.get("stack_trace", "")

            # Map context
            context = payload.get("context", {})
            for key, value in context.items():
                error.context[key] = str(value)

        # Add mappings for other event types...

    def _map_game_state(self, json_state: Dict[str, Any], proto_state: Message):
        """Map JSON game state to protobuf game state"""
        # Basic fields
        proto_state.in_game = json_state.get("in_game", False)
        proto_state.game_id = json_state.get("game_id", "")
        proto_state.ante = json_state.get("ante", 1)
        proto_state.round = json_state.get("round", 1)
        proto_state.chips = json_state.get("chips", 0)
        proto_state.mult = json_state.get("mult", 1)
        proto_state.money = json_state.get("money", 0)
        proto_state.hand_size = json_state.get("hand_size", 8)
        proto_state.hands_remaining = json_state.get("hands_remaining", 0)
        proto_state.discards_remaining = json_state.get("discards_remaining", 0)

        # Map collections
        for joker_data in json_state.get("jokers", []):
            joker = proto_state.jokers.add()
            self._map_joker(joker_data, joker)

        for card_data in json_state.get("hand", []):
            card = proto_state.hand.add()
            self._map_card(card_data, card)

        # Map phase
        phase_name = json_state.get("game_state", "PHASE_UNSPECIFIED")
        proto_state.game_state = self._map_phase(phase_name)

    def _map_joker(self, json_joker: Dict[str, Any], proto_joker: Message):
        """Map JSON joker to protobuf joker"""
        proto_joker.id = json_joker.get("id", "")
        proto_joker.name = json_joker.get("name", "")
        proto_joker.position = json_joker.get("position", 0)

        # Map properties
        props = json_joker.get("properties", {})
        proto_joker.properties.mult = props.get("mult", 0)
        proto_joker.properties.chips = props.get("chips", 0)
        proto_joker.properties.cost = props.get("cost", 0)
        proto_joker.properties.sell_value = props.get("sell_value", 0)
        proto_joker.properties.edition = props.get("edition", "")

    def _map_card(self, json_card: Dict[str, Any], proto_card: Message):
        """Map JSON card to protobuf card"""
        from jimbot.proto import balatro_events_pb2

        proto_card.id = json_card.get("id", "")
        proto_card.position = json_card.get("position", 0)
        proto_card.enhancement = json_card.get("enhancement", "")
        proto_card.edition = json_card.get("edition", "")
        proto_card.seal = json_card.get("seal", "")

        # Map rank
        rank_str = str(json_card.get("rank", "")).upper()
        rank_map = {
            "A": "RANK_ACE",
            "1": "RANK_ACE",
            "ACE": "RANK_ACE",
            "2": "RANK_TWO",
            "3": "RANK_THREE",
            "4": "RANK_FOUR",
            "5": "RANK_FIVE",
            "6": "RANK_SIX",
            "7": "RANK_SEVEN",
            "8": "RANK_EIGHT",
            "9": "RANK_NINE",
            "10": "RANK_TEN",
            "J": "RANK_JACK",
            "JACK": "RANK_JACK",
            "Q": "RANK_QUEEN",
            "QUEEN": "RANK_QUEEN",
            "K": "RANK_KING",
            "KING": "RANK_KING",
        }
        proto_card.rank = getattr(
            balatro_events_pb2.Rank, rank_map.get(rank_str, "RANK_UNSPECIFIED")
        )

        # Map suit
        suit_str = str(json_card.get("suit", "")).upper()
        suit_map = {
            "S": "SUIT_SPADES",
            "SPADES": "SUIT_SPADES",
            "H": "SUIT_HEARTS",
            "HEARTS": "SUIT_HEARTS",
            "C": "SUIT_CLUBS",
            "CLUBS": "SUIT_CLUBS",
            "D": "SUIT_DIAMONDS",
            "DIAMONDS": "SUIT_DIAMONDS",
        }
        proto_card.suit = getattr(
            balatro_events_pb2.Suit, suit_map.get(suit_str, "SUIT_UNSPECIFIED")
        )

    def _map_action(self, json_action: Dict[str, Any], proto_action: Message):
        """Map JSON action to protobuf action"""
        proto_action.action_id = json_action.get("action_id", "")
        proto_action.action_type = json_action.get("action_type", "")

        # Map action-specific data
        action_type = json_action.get("action_type", "")
        if action_type == "play_hand":
            proto_action.play_hand.card_indices.extend(
                json_action.get("card_indices", [])
            )
        elif action_type == "discard":
            proto_action.discard.card_indices.extend(
                json_action.get("card_indices", [])
            )
        elif action_type == "buy":
            proto_action.buy.shop_index = json_action.get("shop_index", 0)
            proto_action.buy.item_type = json_action.get("item_type", "")
        # Add other action types...

        # Map metadata
        metadata = json_action.get("metadata", {})
        for key, value in metadata.items():
            proto_action.metadata[key] = str(value)

    def _map_phase(self, phase_name: str) -> int:
        """Map phase name to protobuf enum"""
        from jimbot.proto import balatro_events_pb2

        phase_map = {
            "MENU": "PHASE_MENU",
            "BLIND_SELECT": "PHASE_BLIND_SELECT",
            "SHOP": "PHASE_SHOP",
            "PLAYING": "PHASE_PLAYING",
            "GAME_OVER": "PHASE_GAME_OVER",
            "ROUND_EVAL": "PHASE_ROUND_EVAL",
            "TAROT_PACK": "PHASE_TAROT_PACK",
            "PLANET_PACK": "PHASE_PLANET_PACK",
            "SPECTRAL_PACK": "PHASE_SPECTRAL_PACK",
            "STANDARD_PACK": "PHASE_STANDARD_PACK",
            "BUFFOON_PACK": "PHASE_BUFFOON_PACK",
            "BOOSTER_PACK": "PHASE_BOOSTER_PACK",
        }

        proto_name = phase_map.get(phase_name.upper(), "PHASE_UNSPECIFIED")
        return getattr(balatro_events_pb2.GamePhase, proto_name)

    def _proto_type_to_json(self, proto_type: int) -> str:
        """Convert protobuf event type enum to JSON type string"""
        # Reverse mapping
        for json_type, proto_name in self.type_mappings.items():
            if proto_name.endswith(str(proto_type)):
                return json_type
        return "unknown"

    def _transform_payload_fields(self, json_event: Dict[str, Any], event_type: int):
        """Apply any necessary transformations to payload fields"""
        # This can be extended to handle specific field transformations
        # based on event type for backward compatibility
        pass

    def _extract_unknown_fields(self, json_event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields not in the standard schema"""
        known_fields = {
            "type",
            "source",
            "timestamp",
            "event_id",
            "priority",
            "game_id",
            "session_id",
            "sequence_number",
            "payload",
            "metadata",
            "version",
        }

        unknown = {}
        for key, value in json_event.items():
            if key not in known_fields:
                unknown[key] = value

        return unknown

    def _json_to_any(self, json_data: Dict[str, Any]) -> struct_pb2.Struct:
        """Convert JSON dictionary to protobuf Struct"""
        struct = struct_pb2.Struct()
        struct.update(json_data)
        return struct

    def _generate_event_id(self) -> str:
        """Generate a unique event ID"""
        import uuid

        return str(uuid.uuid4())

    def batch_json_to_proto(self, json_events: list) -> Optional[Message]:
        """Convert batch of JSON events to protobuf EventBatch"""
        try:
            from jimbot.proto import balatro_events_pb2

            batch = balatro_events_pb2.EventBatch()
            batch.batch_id = self._generate_event_id()
            batch.timestamp = int(datetime.now().timestamp() * 1000)
            batch.source = "json_compatibility"

            for json_event in json_events:
                proto_event = self.json_to_proto(json_event)
                if proto_event:
                    batch.events.append(proto_event)

            return batch

        except Exception as e:
            logger.error(f"Failed to convert JSON batch to proto: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return None

    def batch_proto_to_json(self, proto_batch: Message) -> Optional[list]:
        """Convert protobuf EventBatch to list of JSON events"""
        try:
            json_events = []

            for proto_event in proto_batch.events:
                json_event = self.proto_to_json(proto_event)
                if json_event:
                    json_events.append(json_event)

            return json_events

        except Exception as e:
            logger.error(f"Failed to convert proto batch to JSON: {e}", exc_info=True)
            if self.strict_mode:
                raise
            return None
