"""
Deno JavaScript runtime management for SageDLP.

Handles silent background installation, version checking, and path resolution
for the Deno runtime, which yt-dlp requires to solve YouTube's n-challenge
when using authenticated cookies.

Closely mirrors the pattern in sage_yt_dlp.py (check → download → verify).
"""

import io
import os
import subprocess
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests
from PySide6.QtCore import QThread, Signal

from ..utils.sage_logger import logger
from ..utils.sage_constants import (
    DENO_APP_BIN_PATH,
    DENO_DOWNLOAD_URL,
    OS_NAME,
    SUBPROCESS_CREATIONFLAGS,
)


# ---------------------------------------------------------------------------
# Binary discovery
# ---------------------------------------------------------------------------


def check_deno_binary() -> Optional[Path]:
    """
    Check if the deno binary exists in the app's managed bin directory.

    Returns:
        Path or None: Path to deno binary if found, None otherwise.
    """
    exe_path = DENO_APP_BIN_PATH
    if exe_path.exists():
        # Ensure executable on Unix
        if OS_NAME != "Windows" and not os.access(exe_path, os.X_OK):
            try:
                os.chmod(exe_path, 0o755)
                logger.info(f"Fixed permissions on deno at {exe_path}")
            except Exception as e:
                logger.exception(f"Could not set executable permissions on {exe_path}: {e}")
        logger.info(f"Found deno in app bin directory: {exe_path}")
        return exe_path

    logger.warning(f"deno binary not found in app bin directory: {exe_path}")
    return None


def check_deno_installed() -> bool:
    """
    Check if deno is installed and functional.

    Returns:
        bool: True if deno is found and working, False otherwise.
    """
    try:
        deno_path = check_deno_binary()
        if deno_path:
            result = subprocess.run(
                [deno_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=SUBPROCESS_CREATIONFLAGS,
            )
            return result.returncode == 0
        return False
    except Exception:
        return False


def get_deno_path() -> Optional[Path]:
    """
    Get the deno path from the app's managed bin directory.

    Returns:
        Path or None: Path to deno binary, or None if not found.
    """
    return check_deno_binary()


def get_deno_version() -> str:
    """
    Get the installed deno version string.

    Returns:
        str: Version string (e.g. "2.9.3") or "Not found" on failure.
    """
    try:
        deno_path = check_deno_binary()
        if not deno_path:
            return "Not found"
        result = subprocess.run(
            [deno_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=SUBPROCESS_CREATIONFLAGS,
        )
        if result.returncode == 0:
            # First line is e.g. "deno 2.9.3 (stable, ...)"
            return result.stdout.strip().split("\n")[0] if result.stdout.strip() else "Unknown"
        return "Error"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Background download thread
# ---------------------------------------------------------------------------


class DownloadDenoThread(QThread):
    """
    Background thread that downloads the Deno runtime zip, extracts the binary,
    and places it in the app's managed bin directory.

    Signals
    -------
    progress_signal(percent: int)
        Download progress 0-100.
    finished_signal(success: bool, message: str)
        Completed — success=True with path, or success=False with error.
    """

    progress_signal = Signal(int)
    finished_signal = Signal(bool, str)

    def run(self) -> None:
        try:
            exe_path = DENO_APP_BIN_PATH
            logger.info(f"Downloading deno from: {DENO_DOWNLOAD_URL}")

            response = requests.get(DENO_DOWNLOAD_URL, stream=True, timeout=(10, 30))
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            chunk_size = 1024 * 64  # 64 KiB

            # Download into memory first (zip is ~40 MB)
            content = bytearray()
            for chunk in response.iter_content(chunk_size):
                content.extend(chunk)
                if total_size > 0:
                    pct = int(len(content) / total_size * 100)
                    self.progress_signal.emit(pct)

            # Basic integrity check
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as _test:
                    bad = _test.testzip()
                    if bad is not None:
                        raise zipfile.BadZipFile(f"Corrupt zip: {bad}")
            except zipfile.BadZipFile:
                raise  # Let the outer except handle it

            # Extract the binary from the zip archive
            exe_name = "deno.exe" if OS_NAME == "Windows" else "deno"
            exe_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    # Find the deno executable inside the zip by suffix
                    members = [n for n in zf.namelist() if n.endswith(exe_name) and '/' not in n]
                    if not members:
                        # Try subdirectories
                        members = [n for n in zf.namelist() if n.endswith(exe_name)]
                    if not members:
                        raise KeyError(f"Could not find '{exe_name}' in downloaded zip archive")
                    zf.extract(members[0], exe_path.parent)
                    # If extracted to a subdirectory, move it
                    extracted = exe_path.parent / members[0]
                    if extracted != exe_path:
                        shutil.move(str(extracted), str(exe_path))
                        # Clean up empty directories from extraction
                        for p in reversed(extracted.parents):
                            if p != exe_path.parent and p.exists():
                                try:
                                    p.rmdir()
                                except OSError:
                                    pass
            except Exception:
                # Clean up partial/corrupt file
                if exe_path.exists():
                    exe_path.unlink()
                raise

            # Make executable on Unix
            if OS_NAME != "Windows":
                os.chmod(exe_path, 0o755)

            logger.info(f"deno downloaded and installed successfully: {exe_path}")
            self.finished_signal.emit(True, str(exe_path))

        except Exception as e:
            logger.exception(f"Error downloading deno: {e}")
            self.finished_signal.emit(False, str(e))