"""Entry point: starts the local FastAPI server and opens it in your browser.

Usage: python run.py
"""
import threading
import time
import webbrowser

import uvicorn

from web.app import app

HOST = "127.0.0.1"
PORT = 8000


def open_browser():
    time.sleep(1.5)  # give uvicorn a moment to start listening
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT)
