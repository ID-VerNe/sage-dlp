"""
Dialog modules for SageDLP GUI.

This package contains all dialog classes organized by functionality:

    - sage_dialogs_base: Base utility dialogs
    - sage_dialogs_settings: Settings configuration dialogs
    - sage_dialogs_update: Update-related dialogs and threads
    - sage_dialogs_ffmpeg: FFmpeg installation dialogs
    - sage_dialogs_selection: Subtitle and playlist selection dialogs
    - sage_dialogs_custom: Custom functionality dialogs
"""

# Re-export all dialog classes for backward compatibility
from .sage_dialogs_base import LogWindow
from .sage_dialogs_custom import CustomOptionsDialog
from .sage_dialogs_ffmpeg import FFmpegCheckDialog, FFmpegInstallThread
from .sage_dialogs_selection import (
    PlaylistSelectionDialog,
    SubtitleSelectionDialog,
)
from .sage_dialogs_settings import AutoUpdateSettingsDialog, DownloadSettingsDialog
from .sage_dialogs_update import AutoUpdateThread, UpdateThread, VersionCheckThread, YTDLPUpdateDialog
from .sage_dialogs_updater import UpdaterTabWidget

__all__ = [
    # Base dialogs
    "LogWindow",

    # Settings dialogs
    "DownloadSettingsDialog",
    "AutoUpdateSettingsDialog",

    # Update dialogs and threads
    "VersionCheckThread",
    "UpdateThread",
    "YTDLPUpdateDialog",
    "AutoUpdateThread",

    # FFmpeg dialogs
    "FFmpegInstallThread",
    "FFmpegCheckDialog",

    # Selection dialogs
    "SubtitleSelectionDialog",
    "PlaylistSelectionDialog",

    # Custom functionality dialogs
    "CustomOptionsDialog",

    # Updater widget
    "UpdaterTabWidget",
]
