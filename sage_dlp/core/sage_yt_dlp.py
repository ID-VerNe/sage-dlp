import os
import subprocess
from pathlib import Path
from typing import Optional

import requests
from PySide6.QtCore import QThread, Signal

from ..utils.sage_logger import logger
from ..utils.sage_constants import (
    OS_NAME,
    SUBPROCESS_CREATIONFLAGS,
    YTDLP_APP_BIN_PATH,
    YTDLP_DOWNLOAD_URL,
    YTDLP_SHA256_URL,
)
from .sage_ffmpeg import get_file_sha256

# YTDLP_URLS moved to src\utils\sage_constants.py
# get_ytdlp_install_dir() moved to src\utils\sage_constants.py
# get_ytdlp_executable_path() moved to src\utils\sage_constants.py
# get_os_type() moved to src\utils\sage_constants.py
# ensure_install_dir_exists() moved to src\utils\sage_constants.py


def verify_ytdlp_sha256(file_path: Path, download_url: str) -> bool:
    """
    Verify yt-dlp file SHA256 hash against official checksums.
    
    Args:
        file_path: Path to the downloaded yt-dlp file
        download_url: The URL used to download the file (to determine the filename)
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    try:
        # Download the SHA2-256SUMS file
        logger.info(f"Downloading SHA256 checksums from: {YTDLP_SHA256_URL}")
        response = requests.get(YTDLP_SHA256_URL, timeout=10)
        response.raise_for_status()
        checksum_content = response.text
        
        # Extract filename from download URL (e.g., yt-dlp.exe, yt-dlp_macos, yt-dlp)
        filename = download_url.split("/")[-1]
        logger.info(f"Looking for checksum for file: {filename}")
        
        # Parse the checksum file to find the matching hash
        expected_hash = None
        for line in checksum_content.strip().split("\n"):
            if filename in line:
                # Format: "hash  filename"
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == filename:
                    expected_hash = parts[0]
                    break
        
        if not expected_hash:
            logger.error(f"Could not find SHA256 hash for {filename} in checksums file")
            return False
        
        # Calculate actual hash of downloaded file
        logger.info("Calculating SHA256 hash of downloaded file...")
        actual_hash = get_file_sha256(file_path)
        
        # Compare hashes
        if actual_hash.lower() == expected_hash.lower():
            logger.info("✓ SHA256 verification successful!")
            logger.info(f"  Expected: {expected_hash}")
            logger.info(f"  Actual:   {actual_hash}")
            return True
        else:
            logger.error("✗ SHA256 verification failed!")
            logger.error(f"  Expected: {expected_hash}")
            logger.error(f"  Actual:   {actual_hash}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Failed to download SHA256 checksums: {e}")
        return False
    except Exception as e:
        logger.exception(f"Error during SHA256 verification: {e}")
        return False


class DownloadYtdlpThread(QThread):
    progress_signal = Signal(int)
    finished_signal = Signal(bool, str)

    def __init__(self):
        super().__init__()

    def run(self) -> None:
        try:
            # Extra logic moved to src\utils\sage_constants.py
            exe_path = YTDLP_APP_BIN_PATH

            # Download with progress reporting
            logger.info(f"Downloading yt-dlp from: {YTDLP_DOWNLOAD_URL}")
            response = requests.get(YTDLP_DOWNLOAD_URL, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024  # 1 Kibibyte

            if total_size == 0:
                self.progress_signal.emit(100)

            with open(exe_path, "wb") as f:
                downloaded = 0
                for data in response.iter_content(block_size):
                    f.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        progress = int(downloaded / total_size * 100)
                        self.progress_signal.emit(progress)

            logger.info("Download complete, verifying SHA256 hash...")
            
            # Verify SHA256 hash
            if not verify_ytdlp_sha256(exe_path, YTDLP_DOWNLOAD_URL):
                # Hash verification failed - delete the downloaded file
                logger.error("SHA256 verification failed! Removing downloaded file.")
                if Path(exe_path).exists():
                    Path(exe_path).unlink()
                self.finished_signal.emit(
                    False, 
                    "SHA256 verification failed. The downloaded file may be corrupted or tampered with."
                )
                return

            # Make executable on macOS and Linux
            if OS_NAME != "Windows":
                os.chmod(exe_path, 0o755)

            logger.info("yt-dlp downloaded and verified successfully!")
            self.finished_signal.emit(True, str(exe_path))

        except Exception as e:
            logger.exception(f"Error downloading yt-dlp: {e}")
            self.finished_signal.emit(False, str(e))


def check_ytdlp_binary() -> Optional[Path]:
    """
    Check if yt-dlp binary exists in the app's bin directory ONLY.
    We now ignore system PATH and only use our managed binary.
    Returns:
        Path or None: Path to yt-dlp binary if found in app bin, None otherwise
    """
    exe_path = YTDLP_APP_BIN_PATH
    if exe_path.exists():
        # Make sure it's executable on Unix systems
        if OS_NAME != "Windows" and not os.access(exe_path, os.X_OK):
            try:
                os.chmod(exe_path, 0o755)
                logger.info(f"Fixed permissions on yt-dlp at {exe_path}")
            except Exception as e:
                logger.exception(f"Could not set executable permissions on {exe_path}: {e}")
        logger.info(f"Found yt-dlp in app bin directory: {exe_path}")
        return exe_path

    # Binary not found in app directory - return None to trigger setup
    logger.warning(f"yt-dlp binary not found in app bin directory: {exe_path}")
    return None


def check_ytdlp_installed() -> bool:
    """
    Check if yt-dlp is installed and accessible.
    Returns:
        bool: True if yt-dlp is found and working, False otherwise
    """
    try:
        ytdlp_path = check_ytdlp_binary()
        if ytdlp_path:
            # Try to run yt-dlp --version to verify it's working
            try:
                # Extra logic moved to src\utils\sage_constants.py
                result = subprocess.run(
                    [ytdlp_path, "--version"], capture_output=True, text=True, timeout=5, creationflags=SUBPROCESS_CREATIONFLAGS
                )
                return result.returncode == 0
            except Exception:
                return False
        return False
    except Exception:
        return False


def get_yt_dlp_path() -> Path:
    """
    Get the yt-dlp path, either from the app's bin directory or system PATH.
    This replaces the function in sage_utils.py.
    Returns:
        str: Path to yt-dlp binary
    """
    # First check if we have yt-dlp in our app's bin directory or system PATH
    ytdlp_path = check_ytdlp_binary()
    if ytdlp_path:
        logger.info(f"Using yt-dlp from: {ytdlp_path}")
        return ytdlp_path

    # If not found anywhere, fall back to the command name as a last resort
    logger.info("yt-dlp not found in app directory or PATH, falling back to command name")
    return "yt-dlp"  # type: ignore[return-value]


