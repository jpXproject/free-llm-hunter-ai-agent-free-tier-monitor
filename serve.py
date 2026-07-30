#!/usr/bin/env python3
"""
AI Agent Free Tier Monitor — Local Server
Menyajikan dashboard.html + agents.json di browser.

Usage:
    python serve.py           # default port 8080
    python serve.py 3000      # custom port
"""
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = HTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
    print(f"🌐  AI Agent Free Tier Monitor")
    print(f"    http://localhost:{port}")
    print(f"    Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
