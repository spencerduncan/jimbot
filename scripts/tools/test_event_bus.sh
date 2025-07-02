#!/bin/bash

echo "=== Testing Event Bus Connection ==="
echo ""
echo "1. Checking if server is running on port 8080..."
curl -s http://localhost:8080 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Server is reachable"
else
    echo "✗ Server not reachable"
    exit 1
fi

echo ""
echo "2. Sending test event to server..."
TEST_EVENT='{
  "type": "test",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "data": {
    "message": "Test from WSL",
    "source": "test_script"
  }
}'

RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/events \
  -H "Content-Type: application/json" \
  -d "$TEST_EVENT" \
  -w "\nHTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "Response status: $HTTP_STATUS"
echo "Response body: $BODY"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✓ Test event sent successfully"
else
    echo "✗ Failed to send test event"
fi

echo ""
echo "3. Checking recent events..."
curl -s http://localhost:8080/api/v1/events 2>/dev/null || echo "No GET endpoint available"

echo ""
echo "=== To see if Balatro is sending events ==="
echo "Run this command in another terminal:"
echo "watch -n 1 'curl -s http://localhost:8080/api/v1/events 2>/dev/null || echo \"Waiting for events...\"'"