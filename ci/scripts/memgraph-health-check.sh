#!/bin/bash
# Memgraph health check script for CI environments
# This script provides multiple fallback methods to check Memgraph health

set -e

# Method 1: Check HTTP endpoint (Memgraph Lab)
if command -v curl >/dev/null 2>&1; then
    if curl -f -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Memgraph Lab HTTP endpoint is healthy"
        exit 0
    fi
fi

# Method 2: Check with wget if curl is not available
if command -v wget >/dev/null 2>&1; then
    if wget -q -O /dev/null http://localhost:3000 2>/dev/null; then
        echo "Memgraph Lab HTTP endpoint is healthy (wget)"
        exit 0
    fi
fi

# Method 3: Check Bolt port with netcat
if command -v nc >/dev/null 2>&1; then
    if nc -z localhost 7687 2>/dev/null; then
        echo "Memgraph Bolt port is accessible"
        exit 0
    fi
fi

# Method 4: Check Bolt port with Python
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(('localhost', 7687))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "Memgraph Bolt port is accessible (Python)"
        exit 0
    fi
fi

# Method 5: Check Bolt port with bash TCP
if exec 3<>/dev/tcp/localhost/7687 2>/dev/null; then
    exec 3<&-
    exec 3>&-
    echo "Memgraph Bolt port is accessible (bash TCP)"
    exit 0
fi

# Method 6: Check if Memgraph process is running
if pgrep -f memgraph >/dev/null 2>&1; then
    echo "Memgraph process is running"
    exit 0
fi

# If all methods fail, exit with error
echo "All Memgraph health check methods failed"
exit 1