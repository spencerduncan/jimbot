#!/bin/bash
# Test QuestDB deployment

set -e

echo "Testing QuestDB deployment..."

# Check if container would be created correctly
echo "1. Checking Docker configuration..."
docker-compose -f ../docker-compose.questdb.yml config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Docker compose configuration is valid"
else
    echo "✗ Docker compose configuration is invalid"
    exit 1
fi

# Check if the configuration file exists
echo "2. Checking configuration files..."
if [ -f "conf/server.conf" ]; then
    echo "✓ Server configuration file exists"
else
    echo "✗ Server configuration file missing"
    exit 1
fi

# Check if deployment script is executable
echo "3. Checking deployment script..."
if [ -x "deploy-questdb.sh" ]; then
    echo "✓ Deployment script is executable"
else
    echo "✗ Deployment script is not executable"
    exit 1
fi

# Check if health check script exists
echo "4. Checking health check script..."
if [ -x "health_check.py" ]; then
    echo "✓ Health check script is executable"
else
    echo "✗ Health check script is not executable"
    exit 1
fi

echo ""
echo "All checks passed! QuestDB deployment is ready."
echo "To deploy QuestDB, run: ./deploy-questdb.sh"