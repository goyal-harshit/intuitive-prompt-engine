"""Entry point: python run.py

Picks the first free TCP port at/after the configured one so the app never
fails to boot just because something else already owns 8000, then opens the
browser on the URL it actually bound to.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

# Make the app importable no matter what directory it's launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

from backend.core.config import get_config


def find_free_port(host: str, preferred: int, attempts: int = 50) -> int:
    """Return the first bindable port >= preferred (falls back to an OS-picked one)."""
    # NOTE: no SO_REUSEADDR here — on Windows it lets bind() succeed on a port
    # that is already in use, which would defeat the whole check.
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    # Nothing free in the range — let the OS hand us any open port.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def _open_browser(url: str) -> None:
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()


if __name__ == "__main__":
    cfg = get_config()
    host = cfg.server.host

    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        # Honor a host-assigned port (deploy targets, preview tooling) as-is.
        port = int(env_port)
    else:
        port = find_free_port(host, cfg.server.port)
        if port != cfg.server.port:
            print(f"[GestureGPT] port {cfg.server.port} was busy — using {port} instead")

    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
    print(f"[GestureGPT] starting on {url}")
    _open_browser(url)

    uvicorn.run("backend.app.main:app", host=host, port=port)
