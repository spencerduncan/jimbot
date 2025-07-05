#!/usr/bin/env python3
"""
Monitor Event Bus for incoming events from Balatro
"""

import http.server
import json
import threading
import time
from datetime import datetime


class EventMonitor:
    def __init__(self):
        self.events = []
        self.command_queue = []
        self.lock = threading.Lock()

    def add_event(self, event):
        with self.lock:
            self.events.append(
                {"received_at": datetime.now().isoformat(), "event": event}
            )
            # Keep only last 100 events
            if len(self.events) > 100:
                self.events.pop(0)

    def get_recent_events(self, count=10):
        with self.lock:
            return self.events[-count:]

    def add_command(self, command):
        with self.lock:
            self.command_queue.append(command)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Command queued: {command}")

    def get_and_clear_commands(self):
        with self.lock:
            commands = self.command_queue[:]
            self.command_queue = []
            return commands


monitor = EventMonitor()


class EventBusHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Handle different endpoints
        if self.path == "/api/v1/commands":
            self.handle_command_post()
            return
        elif self.path not in ["/api/v1/events", "/api/v1/events/batch"]:
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            event = json.loads(post_data.decode("utf-8"))
            monitor.add_event(event)

            # Print event summary
            event_type = event.get("type", "unknown")
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Event received: {event_type}")

            # Print event details for certain types
            if event_type in ["connection_test", "game_state", "action_request"]:
                print(f"  Details: {json.dumps(event, indent=2)}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        except Exception as e:
            print(f"Error processing event: {e}")
            self.send_response(400)
            self.end_headers()

    def handle_command_post(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            command_data = json.loads(post_data.decode("utf-8"))
            command_type = command_data.get("type", "")
            payload = command_data.get("payload", {})

            # Convert to simple format for easy parsing
            if command_type:
                if isinstance(payload, dict) and payload:
                    # For commands with parameters
                    params = []
                    if "position" in payload:
                        params.append(str(payload["position"]))
                    elif "index" in payload:
                        params.append(str(payload["index"]))
                    command_str = (
                        f"{command_type}:{','.join(params)}" if params else command_type
                    )
                else:
                    command_str = command_type

                monitor.add_command(command_str)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        except Exception as e:
            print(f"Error processing command: {e}")
            self.send_response(400)
            self.end_headers()

    def do_GET(self):
        # Handle command polling
        if self.path == "/api/v1/commands/poll":
            commands = monitor.get_and_clear_commands()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            # Send commands as newline-separated text
            response = "\n".join(commands)
            self.wfile.write(response.encode())
            return

        # Provide a simple status page
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        recent = monitor.get_recent_events()
        html = f"""
        <html>
        <head>
            <title>BalatroMCP Event Monitor</title>
            <meta http-equiv="refresh" content="5">
        </head>
        <body>
            <h1>BalatroMCP Event Monitor</h1>
            <p>Total events received: {len(monitor.events)}</p>
            <p>Commands in queue: {len(monitor.command_queue)}</p>
            <h2>Recent Events:</h2>
            <pre>{json.dumps(recent, indent=2)}</pre>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def run_server():
    server_address = ("", 8080)
    httpd = http.server.HTTPServer(server_address, EventBusHandler)

    print("=" * 60)
    print("BalatroMCP Event Monitor")
    print("=" * 60)
    print(f"Listening on http://localhost:8080")
    print(f"View events at http://localhost:8080 in your browser")
    print("Waiting for events from Balatro...")
    print("=" * 60)
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
