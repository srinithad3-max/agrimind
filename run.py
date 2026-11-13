"""Start AgriMind:  python run.py   → open http://localhost:8000"""
import os
import webbrowser
from threading import Timer

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    Timer(2.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
