"""Tests for JSON-Protobuf compatibility layer"""

import pytest
from unittest.mock import MagicMock, patch

from jimbot.infrastructure.serialization.json_compatibility import (
    JsonCompatibilityLayer,
)


class TestJsonCompatibilityLayer:
    """Test JSON compatibility layer functionality"""

    @pytest.fixture
    def compat_layer(self):
        """Create compatibility layer instance"""
        return JsonCompatibilityLayer()

    @pytest.fixture
    def sample_json_event(self):
        """Sample JSON event in legacy format"""
        return {
            "type": "GAME_STATE",
            "source": "BalatroMCP",
            "timestamp": 1234567890,
            "priority": "high",
            "payload": {
                "in_game": True,
                "game_id": "test-game-123",
                "ante": 2,
                "round": 3,
                "money": 10,
                "chips": 100,
                "mult": 2,
                "hand_size": 8,
                "hands_remaining": 3,
                "discards_remaining": 2,
                "jokers": [
                    {
                        "id": "joker1",
                        "name": "Joker",
                        "position": 0,
                        "properties": {
                            "mult": 4,
                            "chips": 0,
                            "cost": 3,
                            "sell_value": 2,
                            "edition": "",
                        },
                    }
                ],
                "hand": [
                    {
                        "id": "card1",
                        "rank": "A",
                        "suit": "S",
                        "position": 0,
                        "enhancement": "",
                        "edition": "",
                        "seal": "",
                    }
                ],
                "game_state": "PLAYING",
                "frame_count": 1000,
            },
        }

    @pytest.fixture
    def sample_learning_request(self):
        """Sample learning decision request"""
        return {
            "type": "LEARNING_DECISION",
            "subtype": "REQUEST",
            "source": "BalatroMCP",
            "priority": "high",
            "timestamp": 1234567890,
            "payload": {
                "request_id": "REQ-123",
                "game_state": {"in_game": True, "ante": 1, "money": 4},
                "available_actions": [
                    {
                        "action_id": "action1",
                        "action_type": "play_hand",
                        "card_indices": [0, 1, 2],
                    },
                    {
                        "action_id": "action2",
                        "action_type": "discard",
                        "card_indices": [3, 4],
                    },
                ],
                "time_limit_ms": 1000,
            },
        }

    @pytest.fixture
    def sample_error_event(self):
        """Sample error event"""
        return {
            "type": "ERROR",
            "source": "BalatroMCP",
            "priority": "high",
            "timestamp": 1234567890,
            "payload": {
                "error_code": "GAME_ERROR",
                "message": "Test error message",
                "stack_trace": "stack trace here",
                "context": {"game_id": "test-123", "ante": "1"},
            },
        }

    def test_type_mapping_initialization(self, compat_layer):
        """Test that type mappings are properly initialized"""
        assert "GAME_STATE" in compat_layer.type_mappings
        assert "game_start" in compat_layer.type_mappings
        assert "ERROR" in compat_layer.type_mappings
        assert compat_layer.type_mappings["GAME_STATE"] == "EVENT_TYPE_GAME_STATE"

    @patch("jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2")
    def test_json_to_proto_basic_fields(
        self, mock_pb2, compat_layer, sample_json_event
    ):
        """Test basic field mapping from JSON to protobuf"""
        # Mock protobuf classes
        mock_event = MagicMock()
        mock_pb2.Event.return_value = mock_event
        mock_pb2.EventType.EVENT_TYPE_GAME_STATE = 1

        result = compat_layer.json_to_proto(sample_json_event)

        # Verify basic fields
        assert mock_event.source == "BalatroMCP"
        assert mock_event.timestamp == 1234567890
        assert mock_event.priority == "high"
        assert mock_event.type == 1

    @patch("jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2")
    def test_json_to_proto_game_state(self, mock_pb2, compat_layer, sample_json_event):
        """Test game state payload mapping"""
        # Mock protobuf classes
        mock_event = MagicMock()
        mock_game_state = MagicMock()
        mock_event.game_state = mock_game_state
        mock_pb2.Event.return_value = mock_event
        mock_pb2.EventType.EVENT_TYPE_GAME_STATE = 1
        mock_pb2.GamePhase.PHASE_PLAYING = 4

        result = compat_layer.json_to_proto(sample_json_event)

        # Verify game state fields
        assert mock_game_state.in_game == True
        assert mock_game_state.game_id == "test-game-123"
        assert mock_game_state.ante == 2
        assert mock_game_state.round == 3
        assert mock_game_state.money == 10

    @patch("jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2")
    def test_json_to_proto_with_unknown_fields(self, mock_pb2, compat_layer):
        """Test handling of unknown fields"""
        # Enable preserve unknown
        compat_layer.preserve_unknown = True

        # Mock protobuf
        mock_event = MagicMock()
        mock_event.metadata = {}
        mock_pb2.Event.return_value = mock_event

        json_event = {
            "type": "unknown_type",
            "source": "test",
            "timestamp": 123,
            "unknown_field": "value",
            "another_unknown": {"nested": "data"},
        }

        result = compat_layer.json_to_proto(json_event)

        # Unknown fields should be preserved in metadata
        assert "json_unknown_field" in mock_event.metadata
        assert "json_another_unknown" in mock_event.metadata

    @patch("jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2")
    def test_json_to_proto_learning_request(
        self, mock_pb2, compat_layer, sample_learning_request
    ):
        """Test learning decision request mapping"""
        # Mock protobuf classes
        mock_event = MagicMock()
        mock_request = MagicMock()
        mock_request.available_actions = MagicMock()
        mock_request.available_actions.add = MagicMock()
        mock_event.learning_decision_request = mock_request
        mock_pb2.Event.return_value = mock_event
        mock_pb2.EventType.EVENT_TYPE_LEARNING_DECISION_REQUEST = 22

        result = compat_layer.json_to_proto(sample_learning_request)

        # Verify request fields
        assert mock_request.request_id == "REQ-123"
        assert mock_request.time_limit_ms == 1000

    def test_proto_to_json_basic(self, compat_layer):
        """Test basic protobuf to JSON conversion"""
        # Create mock protobuf event
        mock_event = MagicMock()
        mock_event.event_id = "test-123"
        mock_event.timestamp = 1234567890
        mock_event.source = "test"
        mock_event.type = 1  # GAME_STATE
        mock_event.priority = "normal"
        mock_event.game_id = ""
        mock_event.session_id = ""
        mock_event.WhichOneof.return_value = None
        mock_event.metadata = {}

        # Mock json_format
        with patch(
            "jimbot.infrastructure.serialization.json_compatibility.json_format"
        ) as mock_format:
            mock_format.MessageToDict.return_value = {
                "event_id": "test-123",
                "timestamp": 1234567890,
                "source": "test",
            }

            result = compat_layer.proto_to_json(mock_event)

            assert result["type"] in compat_layer.type_mappings
            assert result["source"] == "test"
            assert result["timestamp"] == 1234567890
            assert result["priority"] == "normal"

    def test_batch_json_to_proto(self, compat_layer):
        """Test batch conversion from JSON to protobuf"""
        with patch(
            "jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2"
        ) as mock_pb2:
            # Mock batch and event
            mock_batch = MagicMock()
            mock_batch.events = []
            mock_pb2.EventBatch.return_value = mock_batch

            # Mock single event conversion
            compat_layer.json_to_proto = MagicMock()
            mock_event = MagicMock()
            compat_layer.json_to_proto.return_value = mock_event

            json_events = [
                {"type": "GAME_STATE", "source": "test1"},
                {"type": "ERROR", "source": "test2"},
            ]

            result = compat_layer.batch_json_to_proto(json_events)

            assert result == mock_batch
            assert compat_layer.json_to_proto.call_count == 2
            assert mock_batch.events.append.call_count == 2

    def test_strict_mode_error_handling(self, compat_layer):
        """Test error handling in strict mode"""
        compat_layer.strict_mode = True

        # Invalid event should raise exception in strict mode
        with pytest.raises(Exception):
            compat_layer.json_to_proto({"invalid": "event"})

    def test_card_rank_mapping(self, compat_layer):
        """Test card rank string to enum mapping"""
        with patch(
            "jimbot.infrastructure.serialization.json_compatibility.balatro_events_pb2"
        ) as mock_pb2:
            # Setup mocks
            mock_pb2.Rank.RANK_ACE = 1
            mock_pb2.Rank.RANK_KING = 13
            mock_pb2.Rank.RANK_UNSPECIFIED = 0

            mock_card = MagicMock()

            # Test various rank formats
            test_cases = [
                ({"rank": "A"}, 1),
                ({"rank": "ACE"}, 1),
                ({"rank": "1"}, 1),
                ({"rank": "K"}, 13),
                ({"rank": "KING"}, 13),
                ({"rank": "invalid"}, 0),
            ]

            for card_data, expected_rank in test_cases:
                compat_layer._map_card(card_data, mock_card)
                assert mock_card.rank == expected_rank

    def test_generate_event_id(self, compat_layer):
        """Test event ID generation"""
        event_id = compat_layer._generate_event_id()

        # Should be a valid UUID string
        assert isinstance(event_id, str)
        assert len(event_id) == 36  # Standard UUID length
        assert event_id.count("-") == 4  # UUID format
