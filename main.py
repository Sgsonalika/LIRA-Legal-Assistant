#!/usr/bin/env python3
"""
LIRA — Legal Intelligence & Research Assistant
===============================================
Entry point. Run:
    python main.py
Then open http://localhost:5000
"""

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n⚖️  LIRA Legal Assistant is starting...")
    print("   Open your browser at: http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
