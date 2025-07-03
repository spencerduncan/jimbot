#!/usr/bin/env python3
"""
Simple web UI for monitoring the mock Resource Coordinator.
"""

import logging
from datetime import datetime
from typing import Dict

import grpc
from flask import Flask, jsonify, render_template_string

import sys

sys.path.append("/home/spduncan/jimbot")
from jimbot.proto import resource_coordinator_pb2
from jimbot.proto import resource_coordinator_pb2_grpc


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# HTML template for the monitoring page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Resource Coordinator Monitor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2 {
            color: #333;
        }
        .status-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .resource-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .resource-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .resource-name {
            font-weight: bold;
            color: #555;
            margin-bottom: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
        }
        .progress-fill.warning {
            background-color: #ff9800;
        }
        .progress-fill.danger {
            background-color: #f44336;
        }
        .stats {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 0.9em;
        }
        .allocations-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .allocations-table th,
        .allocations-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .allocations-table th {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        .allocations-table tr:hover {
            background-color: #f5f5f5;
        }
        .health-status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        .health-status.healthy {
            background-color: #4CAF50;
            color: white;
        }
        .health-status.unhealthy {
            background-color: #f44336;
            color: white;
        }
        .refresh-button {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .refresh-button:hover {
            background-color: #1976D2;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Resource Coordinator Monitor</h1>
        
        <div class="status-card">
            <h2>System Health</h2>
            <div id="health-status"></div>
        </div>
        
        <div class="status-card">
            <h2>Resource Usage</h2>
            <div id="resource-grid" class="resource-grid"></div>
        </div>
        
        <div class="status-card">
            <h2>Active Allocations</h2>
            <div id="allocations-container"></div>
        </div>
        
        <button class="refresh-button" onclick="refreshData()">Refresh</button>
        <span class="timestamp" id="last-update"></span>
    </div>
    
    <script>
        function getProgressClass(percentage) {
            if (percentage >= 90) return 'danger';
            if (percentage >= 70) return 'warning';
            return '';
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatResource(resourceType, value) {
            switch(resourceType) {
                case 'RESOURCE_TYPE_GPU':
                case 'RESOURCE_TYPE_MEMORY':
                    return formatBytes(value * 1024 * 1024); // Convert MB to bytes
                case 'RESOURCE_TYPE_CLAUDE_API':
                    return value + ' req/hr';
                case 'RESOURCE_TYPE_CPU':
                    return value + ' cores';
                default:
                    return value;
            }
        }
        
        async function refreshData() {
            try {
                // Fetch health status
                const healthResponse = await fetch('/api/health');
                const healthData = await healthResponse.json();
                
                const healthHtml = `
                    <span class="health-status ${healthData.healthy ? 'healthy' : 'unhealthy'}">
                        ${healthData.healthy ? 'HEALTHY' : 'UNHEALTHY'}
                    </span>
                    <span style="margin-left: 20px;">Version: ${healthData.version}</span>
                    <span style="margin-left: 20px;">Uptime: ${Math.floor(healthData.uptime_seconds / 60)} minutes</span>
                    <span style="margin-left: 20px;">Mode: ${healthData.metadata.mode || 'unknown'}</span>
                `;
                document.getElementById('health-status').innerHTML = healthHtml;
                
                // Fetch resource status
                const statusResponse = await fetch('/api/status');
                const statusData = await statusResponse.json();
                
                // Render resource cards
                let resourceHtml = '';
                statusData.statuses.forEach(status => {
                    const percentage = (status.allocated / status.total_capacity) * 100;
                    const progressClass = getProgressClass(percentage);
                    
                    resourceHtml += `
                        <div class="resource-card">
                            <div class="resource-name">${status.resource.replace('RESOURCE_TYPE_', '')}</div>
                            <div class="progress-bar">
                                <div class="progress-fill ${progressClass}" style="width: ${percentage}%"></div>
                            </div>
                            <div class="stats">
                                <span>Used: ${formatResource(status.resource, status.allocated)}</span>
                                <span>Total: ${formatResource(status.resource, status.total_capacity)}</span>
                            </div>
                            <div class="stats">
                                <span>Available: ${formatResource(status.resource, status.available)}</span>
                                <span>${percentage.toFixed(1)}%</span>
                            </div>
                        </div>
                    `;
                });
                document.getElementById('resource-grid').innerHTML = resourceHtml;
                
                // Render allocations table
                let allocationsHtml = '<table class="allocations-table"><thead><tr>' +
                    '<th>Component</th><th>Resource</th><th>Quantity</th>' +
                    '<th>Allocated At</th><th>Expires At</th></tr></thead><tbody>';
                
                let hasAllocations = false;
                statusData.statuses.forEach(status => {
                    status.allocations.forEach(alloc => {
                        hasAllocations = true;
                        const allocatedAt = new Date(alloc.allocated_at).toLocaleString();
                        const expiresAt = new Date(alloc.expires_at).toLocaleString();
                        
                        allocationsHtml += `
                            <tr>
                                <td>${alloc.component}</td>
                                <td>${status.resource.replace('RESOURCE_TYPE_', '')}</td>
                                <td>${formatResource(status.resource, alloc.quantity)}</td>
                                <td>${allocatedAt}</td>
                                <td>${expiresAt}</td>
                            </tr>
                        `;
                    });
                });
                
                if (!hasAllocations) {
                    allocationsHtml += '<tr><td colspan="5" style="text-align: center; color: #666;">No active allocations</td></tr>';
                }
                
                allocationsHtml += '</tbody></table>';
                document.getElementById('allocations-container').innerHTML = allocationsHtml;
                
                // Update timestamp
                document.getElementById('last-update').textContent = 'Last updated: ' + new Date().toLocaleString();
                
            } catch (error) {
                console.error('Error refreshing data:', error);
                alert('Failed to refresh data: ' + error.message);
            }
        }
        
        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
"""


class ResourceCoordinatorClient:
    """Client for connecting to the Resource Coordinator."""

    def __init__(self, host="localhost", port=50051):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = resource_coordinator_pb2_grpc.ResourceCoordinatorStub(self.channel)

    def get_health(self) -> Dict:
        """Get health status."""
        try:
            request = resource_coordinator_pb2.HealthCheckRequest()
            response = self.stub.HealthCheck(request)
            return {
                "healthy": response.healthy,
                "version": response.version,
                "uptime_seconds": response.uptime_seconds,
                "metadata": dict(response.metadata),
            }
        except grpc.RpcError as e:
            return {
                "healthy": False,
                "version": "unknown",
                "uptime_seconds": 0,
                "metadata": {"error": str(e)},
            }

    def get_status(self) -> Dict:
        """Get resource status."""
        try:
            request = resource_coordinator_pb2.ResourceStatusRequest()
            response = self.stub.GetResourceStatus(request)

            statuses = []
            for status in response.statuses:
                allocations = []
                for alloc in status.allocations:
                    allocations.append(
                        {
                            "request_id": alloc.request_id,
                            "component": alloc.component,
                            "quantity": alloc.quantity,
                            "allocated_at": alloc.allocated_at.ToDatetime().isoformat(),
                            "expires_at": alloc.expires_at.ToDatetime().isoformat(),
                        }
                    )

                statuses.append(
                    {
                        "resource": resource_coordinator_pb2.ResourceType.Name(
                            status.resource
                        ),
                        "total_capacity": status.total_capacity,
                        "available": status.available,
                        "allocated": status.allocated,
                        "allocations": allocations,
                    }
                )

            return {
                "statuses": statuses,
                "timestamp": response.timestamp.ToDatetime().isoformat(),
            }
        except grpc.RpcError as e:
            logging.error(f"Failed to get status: {e}")
            return {"statuses": [], "timestamp": datetime.now().isoformat()}


# Initialize client
client = ResourceCoordinatorClient()


@app.route("/")
def index():
    """Render the monitoring page."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/health")
def api_health():
    """Get health status."""
    return jsonify(client.get_health())


@app.route("/api/status")
def api_status():
    """Get resource status."""
    return jsonify(client.get_status())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resource Coordinator Web UI")
    parser.add_argument("--port", type=int, default=8080, help="Web server port")
    parser.add_argument(
        "--coordinator-host", default="localhost", help="Coordinator host"
    )
    parser.add_argument(
        "--coordinator-port", type=int, default=50051, help="Coordinator port"
    )

    args = parser.parse_args()

    # Update client with custom host/port
    client = ResourceCoordinatorClient(args.coordinator_host, args.coordinator_port)

    # Start web server
    app.run(host="0.0.0.0", port=args.port, debug=True)
