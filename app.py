#!/usr/bin/env python3
"""
Local development server for Adobe Hackathon Result Finder.
Run with: python app.py
"""

import uvicorn

if __name__ == "__main__":
    print("Starting Adobe Hackathon Leaderboard Result Finder...")
    print("Open your browser at: http://127.0.0.1:8000")
    uvicorn.run("api.index:app", host="127.0.0.1", port=8000, reload=True)
