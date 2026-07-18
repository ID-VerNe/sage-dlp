"""
FFmpeg installation thread for SageDLP application.

The interactive `FFmpegCheckDialog` has been removed; FFmpeg is now installed
silently in the background on startup via `FFmpegInstallThread`.
"""

from PySide6.QtCore import QThread, Signal

from ...core.sage_ffmpeg import auto_install_ffmpeg


class FFmpegInstallThread(QThread):
    finished = Signal(bool)
    progress = Signal(str)

    def run(self) -> None:
        # Use a callback to capture progress instead of stdout redirection
        def progress_callback(msg: str):
            self.progress.emit(msg)

        # Install FFmpeg with progress callback
        success = auto_install_ffmpeg(progress_callback=progress_callback)
        self.finished.emit(success)
