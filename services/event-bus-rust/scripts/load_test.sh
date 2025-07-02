#!/bin/bash
# Load test script for the Rust Event Bus
# Tests the 10,000+ events/second requirement

BASE_URL="http://localhost:8080"
DURATION=10  # seconds
CONCURRENCY=100  # concurrent connections

echo "Load Testing Rust Event Bus..."
echo "Target: 10,000+ events/second"
echo "Duration: ${DURATION} seconds"
echo "Concurrency: ${CONCURRENCY} connections"
echo

# Check if Apache Bench is installed
if ! command -v ab &> /dev/null; then
    echo "Apache Bench (ab) is not installed. Installing..."
    apt-get update && apt-get install -y apache2-utils
fi

# Create a sample event payload
cat > /tmp/event_payload.json << EOF
{
  "type": "GAME_STATE",
  "source": "load_test",
  "payload": {
    "ante": 1,
    "round": 1,
    "money": 4,
    "chips": 100,
    "mult": 1,
    "hands_remaining": 4,
    "discards_remaining": 3,
    "in_game": true,
    "game_id": "load-test-123"
  }
}
EOF

# Run the load test
echo "Starting load test..."
ab -n 100000 \
   -c ${CONCURRENCY} \
   -t ${DURATION} \
   -p /tmp/event_payload.json \
   -T application/json \
   -H "Content-Type: application/json" \
   "${BASE_URL}/api/v1/events"

# Clean up
rm -f /tmp/event_payload.json

echo
echo "Load test completed!"