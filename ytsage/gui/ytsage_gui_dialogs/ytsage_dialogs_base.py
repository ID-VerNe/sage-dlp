"""
Base dialogs for YTSage application.
Contains basic utility dialogs like LogWindow and AboutDialog.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ... import __version__ as APP_VERSION
from ...utils.ytsage_localization import _
from ...utils.ytsage_logger import logger
from ...utils.ytsage_constants import APP_LOG_DIR

from ...core.ytsage_ffmpeg import get_ffmpeg_path
from ...core.ytsage_utils import _version_cache, check_ffmpeg, get_ffmpeg_version, get_ytdlp_version, get_deno_version, refresh_version_cache
from ...core.ytsage_yt_dlp import check_ytdlp_installed, get_yt_dlp_path, check_ytdlp_deno_integration
from ...core.ytsage_deno import check_deno_installed, get_deno_path


class SystemInfoThread(QThread):
    """Background thread to gather system information."""
    info_ready = Signal(dict)

    def run(self):
        info = {}
        
        # yt-dlp Status
        ytdlp_found = check_ytdlp_installed()
        info['ytdlp_found'] = ytdlp_found
        info['ytdlp_version'] = get_ytdlp_version()
        info['ytdlp_path'] = get_yt_dlp_path() if ytdlp_found else None

        # yt-dlp cache status
        ytdlp_cache = _version_cache.get("ytdlp", {})
        info['ytdlp_last_check'] = ytdlp_cache.get("last_check", 0)
        
        # FFmpeg Status
        ffmpeg_found = check_ffmpeg()
        info['ffmpeg_found'] = ffmpeg_found
        info['ffmpeg_version'] = get_ffmpeg_version() if ffmpeg_found else _('about.not_available')
        info['ffmpeg_path'] = get_ffmpeg_path() if ffmpeg_found else None

        # FFmpeg cache status
        ffmpeg_cache = _version_cache.get("ffmpeg", {})
        info['ffmpeg_last_check'] = ffmpeg_cache.get("last_check", 0)
        
        # Deno Status
        deno_found = check_deno_installed()
        info['deno_found'] = deno_found
        info['deno_version'] = get_deno_version() if deno_found else _('about.not_available')
        info['deno_path'] = get_deno_path() if deno_found else None
        
        # Deno cache status
        deno_cache = _version_cache.get("deno", {})
        info['deno_last_check'] = deno_cache.get("last_check", 0)

        # Check integration with yt-dlp if both are present
        info['integration_status'] = False
        if deno_found and ytdlp_found:
             info['integration_status'] = check_ytdlp_deno_integration()
             
        self.info_ready.emit(info)


class LogWindow(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("dialogs.ytdlp_log_title"))
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #2b2b2b;
                color: #2d3436;
                font-family: Consolas, monospace;
                font-size: 12px;
                border: 2px solid #b0bec5;
                border-radius: 4px;
            }
        """
        )

        layout.addWidget(self.log_text)

    def append_log(self, message) -> None:
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
