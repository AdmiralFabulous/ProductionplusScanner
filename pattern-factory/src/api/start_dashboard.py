#!/usr/bin/env python3
"""
Start SameDaySuits Production Dashboard

This script starts the web server with the production dashboard.
Open http://localhost:8000 in your browser after starting.

Usage:
    python start_dashboard.py
    python start_dashboard.py --port 8080
"""

import sys
import webbrowser
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def open_browser(port: int, delay: float = 1.5):
    """Open browser after a short delay."""
    time.sleep(delay)
    url = f"http://localhost:{port}"
    print(f"\nOpening browser: {url}")
    webbrowser.open(url)


def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Start SameDaySuits Dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("   SAMEDAYSUITS PRODUCTION DASHBOARD")
    print("=" * 60)
    print(f"   Dashboard: http://localhost:{args.port}")
    print(f"   API Docs:  http://localhost:{args.port}/docs")
    print(f"   Health:    http://localhost:{args.port}/health")
    print("=" * 60)
    print("\n   Press Ctrl+C to stop the server\n")

    # Open browser in background thread
    if not args.no_browser:
        browser_thread = threading.Thread(
            target=open_browser, args=(args.port,), daemon=True
        )
        browser_thread.start()

    # Start server
    uvicorn.run(
        "web_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
