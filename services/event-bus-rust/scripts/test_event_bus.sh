#!/bin/bash
# Test script for the Rust Event Bus

BASE_URL="http://localhost:8080"

echo "Testing Rust Event Bus..."
echo

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s "${BASE_URL}/health" | jq .
echo

# Test single event
echo "2. Testing single event..."
curl -s -X POST "${BASE_URL}/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "HEARTBEAT",
    "source": "test_script",
    "payload": {
      "version": "1.0.0",
      "uptime": 12345,
      "headless": false,
      "game_state": "MENU"
    }
  }' | jq .
echo

# Test batch events
echo "3. Testing batch events..."
curl -s -X POST "${BASE_URL}/api/v1/events/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "type": "CONNECTION_TEST",
        "source": "test_script",
        "payload": {
          "message": "Testing connection"
        }
      },
      {
        "type": "GAME_STATE",
        "source": "test_script",
        "payload": {
          "ante": 1,
          "round": 1,
          "money": 4,
          "chips": 100,
          "in_game": true,
          "game_id": "test-123"
        }
      },
      {
        "type": "MONEY_CHANGED",
        "source": "test_script",
        "payload": {
          "old_value": 4,
          "new_value": 10,
          "difference": 6
        }
      }
    ]
  }' | jq .
echo

# Test invalid event type
echo "4. Testing invalid event type (should return error)..."
curl -s -X POST "${BASE_URL}/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "INVALID_EVENT_TYPE",
    "source": "test_script",
    "payload": {}
  }' | jq .
echo

# Test metrics endpoint
echo "5. Testing metrics endpoint..."
curl -s "${BASE_URL}/metrics" | jq .
echo

echo "Event Bus tests completed!"