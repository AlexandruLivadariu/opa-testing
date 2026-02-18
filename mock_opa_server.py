"""
Mock OPA server for testing without Docker.
This creates a simple HTTP server that mimics OPA's API.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time

class MockOPAHandler(BaseHTTPRequestHandler):
    """Handler for mock OPA requests."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "ok", "uptime_seconds": 3600}
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/v1/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "bundles": {
                    "example": {
                        "active_revision": "v1.0.0",
                        "last_successful_download": "2024-01-01T00:00:00Z",
                        "last_successful_activation": "2024-01-01T00:00:00Z"
                    }
                }
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/v1/policies":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "result": [
                    {"id": "example", "raw": "package example\n\ndefault allow = false"}
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        if "/v1/data/" in self.path:
            # Policy evaluation
            try:
                request_data = json.loads(body) if body else {}
                input_data = request_data.get("input", {})
                
                # Mock policy decision based on input
                if input_data.get("role") == "admin":
                    result = {"allow": True}
                elif input_data.get("role") == "user" and input_data.get("action") == "read":
                    result = {"allow": True}
                else:
                    result = {"allow": False}
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "result": result,
                    "decision_id": "mock-decision-123"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

def start_mock_server(port=8181):
    """Start the mock OPA server."""
    server = HTTPServer(('localhost', port), MockOPAHandler)
    print(f"🚀 Mock OPA server starting on http://localhost:{port}")
    print("   Available endpoints:")
    print("   - GET  /health")
    print("   - GET  /v1/status")
    print("   - POST /v1/data/<policy_path>")
    print("\n   Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping mock OPA server...")
        server.shutdown()

if __name__ == "__main__":
    start_mock_server()
