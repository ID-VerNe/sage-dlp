# -*- coding: utf-8 -*-
"""
SageDLP main window — composition root.

`SageApp` is a slim orchestrator that wires together the GUI mixins:

    - `UIMixin`                  — central widget construction + UI helpers
    - `StartupMixin`             — bootstrap, update checks, close event
    - `DownloadMixin`            — download lifecycle + controls
    - `DialogOpsMixin`           — dialog launchers, playlist save, cookie bridge
    - `WidgetAnimationMixin`     — fade / shake / overlay animations
    - `FormatTableMixin`         — format table construction & filtering
    - `VideoInfoMixin`           — video / playlist info sections
    - `AnalysisMixin`            — URL analysis (yt-dlp metadata fetch)

Only `__init__` lives here; all behaviour is provided by the mixins above.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QMainWindow, QStyle

from .. import __version__ as APP_VERSION
from ..core.sage_downloader import SignalManager
from ..core.sage_utils import load_saved_path
from ..utils.sage_config_manager import ConfigManager
from ..utils.sage_constants import ICON_PATH
from ..utils.sage_cookie_server import CookieServer
from ..utils.sage_localization import LocalizationManager, _
from ..utils.sage_logger import logger
from .sage_gui_analysis import AnalysisMixin
from .sage_gui_animations import WidgetAnimationMixin
from .sage_gui_dialogs_ops import DialogOpsMixin
from .sage_gui_download import DownloadMixin
from .sage_gui_format_table import FormatTableMixin
from .sage_gui_startup import StartupMixin
from .sage_gui_ui import UIMixin
from .sage_gui_video_info import VideoInfoMixin
from .sage_stylesheet import StyleSheet


class SageApp(
    QMainWindow,
    UIMixin,
    StartupMixin,
    DownloadMixin,
    DialogOpsMixin,
    WidgetAnimationMixin,
    FormatTableMixin,
    VideoInfoMixin,
    AnalysisMixin,
):
    """Main application window — composes the GUI mixins."""

    # @lat: [[Gui#sage_gui_main]]
    def __init__(self) -> None:
        super().__init__()

        # Initialize localization system (default to Chinese)
        saved_language = ConfigManager.get("language") or "zh"
        LocalizationManager.initialize(saved_language)

        self.version = APP_VERSION
        load_saved_path(self)
        # Load custom icon
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        else:
            logger.warning(f"Icon file not found at {ICON_PATH}. Using default icon.")
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))  # Fallback
        self.signals = SignalManager()
        self.download_paused = False
        self.current_download = None
        self.download_cancelled = False
        self.is_updating_ytdlp = False  # Initialize update flag
        self.is_analyzing = False  # Initialize analysis flag
        self.save_thumbnail = False  # Initialize thumbnail state
        self.thumbnail_url = None  # Add this to store thumbnail URL
        self.all_formats = []  # Initialize all_formats
        self.available_subtitles = {}
        self.available_automatic_subtitles = {}
        self.is_playlist = False
        self.playlist_info = None
        self.video_info = None
        self.playlist_entries = []  # Initialize playlist entries
        self.selected_playlist_items = None  # Initialize selection string
        self.save_description = False  # Initialize description state
        self.embed_chapters = False  # Initialize chapters state
        self.subtitle_filter = ""
        self.thumbnail_image = None
        self.video_url = ""
        self.selected_subtitles = []  # Initialize selected subtitles list
        # Initialize cookie settings from saved config
        self._initialize_cookie_settings_from_config()
        # Initialize proxy settings from config
        self.proxy_url = ConfigManager.get("proxy_url")
        self.geo_proxy_url = ConfigManager.get("geo_proxy_url")
        # Initialize speed limit settings from config
        self.speed_limit_value = ConfigManager.get("speed_limit_value")  # Store speed limit value
        self.speed_limit_unit_index = ConfigManager.get("speed_limit_unit_index") or 0  # Store speed limit unit index (0: KB/s, 1: MB/s)
        self.download_section = None
        self.force_keyframes = False
        # Initialize output format settings
        self.force_output_format = ConfigManager.get("force_output_format") or False
        self.preferred_output_format = ConfigManager.get("preferred_output_format") or "mp4"
        self.force_audio_format = ConfigManager.get("force_audio_format") or False
        self.preferred_audio_format = ConfigManager.get("preferred_audio_format") or "best"
        self.audio_normalization = ConfigManager.get("audio_normalization") or False

        generic_val = ConfigManager.get("generic_mode")
        self.generic_mode_enabled = generic_val if generic_val is not None else True

        # Track if video analysis is completed
        self.analysis_completed = False

        # Initialize audio player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Initialize cookie HTTP server (extension bridge)
        self.cookie_server = CookieServer()
        self.cookie_server.cookies_received.connect(self._on_cookies_received_from_extension)

        self.init_ui()
        self._load_window_state()

        # Defer heavy start-up tasks to ensure UI renders immediately
        QTimer.singleShot(100, self._perform_startup_checks)

        self.setStyleSheet(StyleSheet.MAIN)
        self.signals.update_progress.connect(self.update_progress_bar)

        # After adding format buttons
        self.video_button.clicked.connect(self.filter_formats)  # Connect video button
        self.audio_button.clicked.connect(self.filter_formats)  # Connect audio button
        if hasattr(self, "subtitle_only_button"):
            self.subtitle_only_button.clicked.connect(self.filter_formats)

        # Add connections to handle video/audio mode-specific controls
        self.video_button.clicked.connect(self.handle_mode_change)
        self.audio_button.clicked.connect(self.handle_mode_change)
        if hasattr(self, "subtitle_only_button"):
            self.subtitle_only_button.clicked.connect(self.handle_mode_change)

        # Initialize UI state based on current mode
        self.handle_mode_change()
