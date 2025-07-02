#!/usr/bin/env python3
"""
Mock Event Bus Server for testing BalatroMCP mod
Receives events from the mod and logs them for debugging
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime

class EventBusHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            # Parse JSON
            if self.path == '/api/v1/events/batch':
                data = json.loads(post_data.decode('utf-8'))
                print(f"\n[{datetime.datetime.now()}] Received batch with {len(data.get('events', []))} events")
                
                for event in data.get('events', []):
                    self.log_event(event)
            else:
                event = json.loads(post_data.decode('utf-8'))
                print(f"\n[{datetime.datetime.now()}] Received single event")
                self.log_event(event)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            
        except Exception as e:
            print(f"Error processing request: {e}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def log_event(self, event):
        event_type = event.get('type', 'UNKNOWN')
        source = event.get('source', 'unknown')
        
        print(f"  Event: {event_type} from {source}")
        
        if event_type == 'GAME_STATE':
            payload = event.get('payload', {})
            print(f"    Ante: {payload.get('ante')}, Round: {payload.get('round')}")
            print(f"    Money: ${payload.get('money')}, Chips: {payload.get('chips')}")
            print(f"    Jokers: {len(payload.get('jokers', []))}")
            print(f"    Hand: {len(payload.get('hand', []))} cards")
            
        elif event_type == 'LEARNING_DECISION':
            payload = event.get('payload', {})
            print(f"    Request ID: {payload.get('request_id')}")
            print(f"    Available actions: {payload.get('available_actions')}")
            
        elif event_type == 'HEARTBEAT':
            payload = event.get('payload', {})
            print(f"    Version: {payload.get('version')}")
            print(f"    Uptime: {payload.get('uptime')}ms")
            
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, EventBusHandler)
    print(f"Mock Event Bus Server running on port {port}")
    print(f"Listening for events at http://localhost:{port}/api/v1/events")
    print("Press Ctrl+C to stop\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()