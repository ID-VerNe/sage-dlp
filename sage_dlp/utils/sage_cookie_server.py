"""
HTTP Cookie Server Module
=========================

Runs a lightweight threaded HTTP server on localhost:9876 that accepts cookie
data POSTed by the companion browser extension ("Get cookies.txt LOCALLY").

The server saves received cookies to a timestamped file and emits a Qt signal
so the main window can automatically activate them.

Usage
-----
    server = CookieServer()
    server.cookies_received.connect(self._on_cookies_received)
    server.start()
    # ... app runs ...
    server.stop()

Extension companion
-------------------
The modified "Get cookies.txt LOCALLY" extension (in browser_ext/) POSTS
to http://localhost:9876/api/cookies whenever cookies change on the active tab.
"""

import http.server
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .sage_constants import APP_DATA_DIR

logger = logging.getLogger(__name__)

# Default port — must match the extension's configured port
COOKIE_SERVER_PORT: int = 9876
# Directory where received cookies are saved
COOKIE_STORAGE_DIR: Path = APP_DATA_DIR / "cookies"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class CookiePayload:
    """Deserialized cookie POST body."""
    cookies: str = ""
    url: str = ""
    source: str = "extension"


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class _CookieRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Single-request handler.  Only POST /api/cookies is supported; everything
    else returns 404.
    """

    # Shared reference set by the server wrapper so the handler can notify Qt
    server_wrapper: Optional["CookieServer"] = None

    # ------------------------------------------------------------------ #
    # Quiet the base class's default stderr logging
    # ------------------------------------------------------------------ #
    def log_message(self, fmt: str, *args) -> None:
        logger.debug(f"[cookie-server] {fmt % args}")

    # ------------------------------------------------------------------ #
    # CORS preflight
    # ------------------------------------------------------------------ #
    def do_OPTIONS(self) -> None:
        self._set_cors_headers()
        self.send_response(204)
        self.end_headers()

    # ------------------------------------------------------------------ #
    # POST handler
    # ------------------------------------------------------------------ #
    def do_POST(self) -> None:
        if self.path != "/api/cookies":
            self._respond(404, {"error": "Not found. Use POST /api/cookies"})
            return

        try:
            raw_length = self.headers.get("Content-Length", "0")
            length = int(raw_length)
            if length <= 0:
                self._respond(400, {"error": "Invalid Content-Length"})
                return
            body = self.rfile.read(length)
            data: dict = json.loads(body)
        except (json.JSONDecodeError, ValueError, OSError):
            self._respond(400, {"error": "Invalid JSON body"})
            return

        cookies_text: str = data.get("cookies", "")
        url: str = data.get("url", "")
        if not cookies_text:
            self._respond(400, {"error": "Missing 'cookies' field"})
            return

        # Save to a timestamped file
        saved_path = self._save_cookies(cookies_text, url)

        # Notify the Qt side via signal (thread-safe queued connection)
        wrapper = self.server_wrapper
        if wrapper is not None:
            wrapper.cookies_received.emit(str(saved_path), url)

        self._respond(200, {"status": "ok", "file": str(saved_path)})

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _save_cookies(self, cookies_text: str, url: str) -> Path:
        """Persist cookie text to a dated file and return its path."""
        COOKIE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Derive a safe filename from the URL hostname
        try:
            # Extract hostname from URL — no DNS resolution (avoids DNS leak / blocking)
            host = url.split("/")[2] if "//" in url else "unknown"
            # Sanitize: keep only safe chars for a filename
            host = "".join(c if c.isalnum() or c in ".-_" else "_" for c in host)
        except Exception:
            host = "unknown"
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cookies_{host}_{ts}.txt"
        dest = COOKIE_STORAGE_DIR / filename
        dest.write_text(cookies_text, encoding="utf-8")
        return dest

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, status: int, payload: dict) -> None:
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    # Suppress the base class's default do_GET / do_HEAD fallback spam
    def do_GET(self) -> None:
        self._respond(404, {"error": "Only POST /api/cookies is supported"})


# ---------------------------------------------------------------------------
# Threaded HTTP server
# ---------------------------------------------------------------------------

class _ThreadedHTTPServer(
    threading.Thread,
    http.server.HTTPServer,
):
    """
    A combined Thread + HTTPServer so we can .start() it like a thread and
    .shutdown() it cleanly.  The request handler runs on a thread pool
    (ThreadingMixIn-style), but we keep it simple with one daemon thread.
    """

    allow_reuse_address = True
    daemon = True

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = COOKIE_SERVER_PORT,
        wrapper: Optional["CookieServer"] = None,
    ) -> None:
        self.host = host
        self.port = port
        http.server.HTTPServer.__init__(
            self,
            (host, port),
            _CookieRequestHandler,
        )
        threading.Thread.__init__(self, daemon=True, name="cookie-server")
        _CookieRequestHandler.server_wrapper = wrapper

    def run(self) -> None:
        logger.info(
            "Cookie server listening on http://%s:%d",
            self.host,
            self.port,
        )
        try:
            self.serve_forever()
        except OSError:
            pass  # Expected on shutdown


# ---------------------------------------------------------------------------
# Qt-wrapped interface
# ---------------------------------------------------------------------------

class CookieServer(QObject):
    """
    High-level controller that owns the HTTP server thread and emits Qt
    signals when cookies arrive.

    Signals
    -------
    cookies_received(cookie_file: str, url: str)
        Emitted (thread-safe) when the extension POSTs cookies.
    """

    cookies_received: Signal = Signal(str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._server: Optional[_ThreadedHTTPServer] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    # @lat: [[Utils#sage_cookie_server]]
    def start(self, port: int = COOKIE_SERVER_PORT) -> bool:
        """Start the server on *port*.  Returns True on success."""
        if self._server is not None:
            logger.warning("Cookie server already running")
            return True
        try:
            self._server = _ThreadedHTTPServer(port=port, wrapper=self)
            self._server.start()
            return True
        except OSError as exc:
            logger.error("Failed to start cookie server on port %d: %s", port, exc)
            self._server = None
            return False

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self._server is None:
            return
        try:
            self._server.shutdown()
            try:
                self._server.join(timeout=2)
            except Exception:
                pass
        except Exception:
            pass
        self._server = None
        logger.info("Cookie server stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server.is_alive()

    @property
    def port(self) -> int:
        return self._server.port if self._server else COOKIE_SERVER_PORT

    @property
    def url(self) -> str:
        """Human-readable server URL."""
        return f"http://127.0.0.1:{self.port}"