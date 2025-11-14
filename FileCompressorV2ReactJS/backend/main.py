# backend/main.py
import sys
import os
import threading
import webbrowser
import time
import socket

# --- CRITICAL: Import api FIRST so PyInstaller sees it ---
try:
    from api import app  # This ensures PyInstaller bundles api.py
except ImportError as e:
    print(f"[FATAL] Could not import api: {e}")
    sys.exit(1)

import uvicorn


def is_port_open(host: str, port: int, timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            pass
        finally:
            try:
                s.close()
            except:
                pass
        time.sleep(0.1)
    return False


def open_browser():
    if is_port_open("127.0.0.1", 8000, timeout=10):
        webbrowser.open("http://127.0.0.1:8000/static/index.html")
    else:
        print("[WARN] Server not ready, opening anyway...")
        webbrowser.open("http://127.0.0.1:8000/static/index.html")


def start_server():
    print("[INFO] Starting FastAPI server...")
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="error",
        )
    except Exception as e:
        print(f"[FATAL] Server crashed: {e}")
        raise


if __name__ == "__main__":
    # 1. Start server in a normal (non-daemon) thread
    server_thread = threading.Thread(target=start_server, daemon=False)
    server_thread.start()

    # 2. Wait a bit, then open browser
    time.sleep(1.0)
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 3. Keep main thread alive
    server_thread.join()
