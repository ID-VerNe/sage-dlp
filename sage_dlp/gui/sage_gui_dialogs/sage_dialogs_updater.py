"""
Updater tab for Custom Options dialog.
Handles FFmpeg version checking and yt-dlp auto-update settings.
"""

import re
import subprocess
import threading
from typing import Optional, Tuple, TYPE_CHECKING, cast

import requests
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.sage_utils import (
    get_auto_update_settings,
    get_ffmpeg_version_direct,
    update_auto_update_settings,
)
from ...core.sage_yt_dlp import get_yt_dlp_path
from .sage_dialogs_update import YTDLPUpdateDialog
from ...utils.sage_config_manager import ConfigManager
from ...utils.sage_localization import _
from ...utils.sage_logger import logger
from ...utils.sage_constants import (
    FFMPEG_7Z_VERSION_URL,
    OS_NAME,
    SUBPROCESS_CREATIONFLAGS,
)

if TYPE_CHECKING:
    from .sage_dialogs_custom import CustomOptionsDialog

from .sage_dialogs_base import (
    primary_button_qss,
    checkbox_qss,
    radio_button_qss,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


# Helper functions for FFmpeg version checking (copied from removed sage_ffmpeg_updater.py)
def get_latest_ffmpeg_version() -> Optional[str]:
    """
    Fetch the latest FFmpeg version from the version URL.
    
    Returns:
        str: Version string (e.g., "8.0") or None if fetch failed
    """
    try:
        response = requests.get(FFMPEG_7Z_VERSION_URL, timeout=10)
        response.raise_for_status()
        version = response.text.strip()
        
        # Validate version format (should be something like "8.0" or "7.1.1")
        if re.match(r'^\d+\.\d+(\.\d+)?$', version):
            logger.info(f"Latest FFmpeg version: {version}")
            return version
        else:
            logger.warning(f"Unexpected version format: {version}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Failed to fetch latest FFmpeg version: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error fetching FFmpeg version: {e}")
        return None


def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Parse version string into tuple of integers for comparison.
    
    Args:
        version_str: Version string like "8.0" or "7.1.1"
        
    Returns:
        Tuple of integers (e.g., (8, 0) or (7, 1, 1))
    """
    try:
        # Extract version numbers from string
        match = re.search(r'(\d+\.\d+(?:\.\d+)?)', version_str)
        if match:
            version_str = match.group(1)
        
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse version: {version_str}")
        return (0,)


def compare_versions(current: str, latest: str) -> bool:
    """
    Compare two version strings.
    
    Args:
        current: Current version string
        latest: Latest version string
        
    Returns:
        True if update is needed (latest > current), False otherwise
    """
    try:
        current_tuple = parse_version(current)
        latest_tuple = parse_version(latest)
        
        logger.info(f"Comparing versions - Current: {current_tuple}, Latest: {latest_tuple}")
        
        # Pad shorter version with zeros for comparison
        max_len = max(len(current_tuple), len(latest_tuple))
        current_padded = current_tuple + (0,) * (max_len - len(current_tuple))
        latest_padded = latest_tuple + (0,) * (max_len - len(latest_tuple))
        
        return latest_padded > current_padded
    except Exception as e:
        logger.exception(f"Error comparing versions: {e}")
        return False


def check_ffmpeg_version() -> Tuple[bool, str, str]:
    """
    Check FFmpeg version and compare with latest.
    
    Returns:
        Tuple of (update_available, current_version, latest_version)
    """
    try:
        # Get current version
        current_version = get_ffmpeg_version_direct()
        if current_version in ["Not found", "Error getting version", "Unknown version"]:
            current_version = "Not installed"
        
        # Get latest version
        latest_version = get_latest_ffmpeg_version()
        if latest_version is None:
            latest_version = "Unknown"
            return False, current_version, latest_version
        
        # If not installed, update is available
        if current_version == "Not installed":
            return True, current_version, latest_version
        
        # Compare versions
        update_needed = compare_versions(current_version, latest_version)
        
        return update_needed, current_version, latest_version
        
    except Exception as e:
        logger.exception(f"Error checking FFmpeg version: {e}")
        return False, "Error", "Error"


class FFmpegCheckThread(QThread):
    finished = Signal(bool, str, str)
    error = Signal(str)

    def run(self):
        try:
            update_available, current_version, latest_version = check_ffmpeg_version()
            self.finished.emit(update_available, current_version, latest_version)
        except Exception as e:
            logger.exception(f"Error checking FFmpeg version: {e}")
            self.error.emit(str(e))





class UpdaterTabWidget(QWidget):
    """Widget for the Updater tab in Custom Options dialog."""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._parent: "CustomOptionsDialog" = cast("CustomOptionsDialog", self.parent())
        
        # State variables
        self.current_version = "Unknown"
        self.latest_version = "Unknown"
        self.update_available = False
        
        self._init_ui()
        self._load_auto_update_settings()
    
    def _init_ui(self) -> None:
        """Initialize the UI components."""
        # Main layout for the tab
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; }")
        
        # Create a widget to hold all content
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Help text
        help_text = QLabel(_('ffmpeg_updater.description'))
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #64748b; padding: 10px;")
        layout.addWidget(help_text)
        
        # FFmpeg Version Check Section
        ffmpeg_group = QGroupBox(_('ffmpeg_updater.title'))
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        
        # Version information layout
        version_layout = QVBoxLayout()
        
        # Current version
        current_layout = QHBoxLayout()
        current_label = QLabel(_('ffmpeg_updater.current_version'))
        current_label.setStyleSheet("font-weight: bold; color: #0f172a;")
        current_layout.addWidget(current_label)
        
        self.current_version_label = QLabel("...")
        self.current_version_label.setStyleSheet("color: #64748b;")
        current_layout.addWidget(self.current_version_label)
        current_layout.addStretch()
        version_layout.addLayout(current_layout)
        
        # Latest version
        latest_layout = QHBoxLayout()
        latest_label = QLabel(_('ffmpeg_updater.latest_version'))
        latest_label.setStyleSheet("font-weight: bold; color: #0f172a;")
        latest_layout.addWidget(latest_label)
        
        self.latest_version_label = QLabel("...")
        self.latest_version_label.setStyleSheet("color: #64748b;")
        latest_layout.addWidget(self.latest_version_label)
        latest_layout.addStretch()
        version_layout.addLayout(latest_layout)
        
        ffmpeg_layout.addLayout(version_layout)
        
        # Status label
        self.status_label = QLabel(_('ffmpeg_updater.status_idle'))
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #64748b; font-size: 12px; padding: 8px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
        ffmpeg_layout.addWidget(self.status_label)
        
        # Check version button
        check_button_layout = QHBoxLayout()
        self.check_button = QPushButton(_('ffmpeg_updater.check_updates'))
        self.check_button.clicked.connect(self.check_for_updates)
        self.check_button.setStyleSheet(primary_button_qss(min_width="120px"))
        check_button_layout.addWidget(self.check_button)
        check_button_layout.addStretch()
        ffmpeg_layout.addLayout(check_button_layout)
        
        # Installation guide info
        guide_label = QLabel(_('ffmpeg_updater.guide_info'))
        guide_label.setWordWrap(True)
        guide_label.setOpenExternalLinks(True)  # Enable clickable links
        guide_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML formatting
        guide_label.setStyleSheet(
            """
            QLabel {
                color: #64748b; 
                font-size: 11px; 
                padding: 8px; 
                background-color: #f1f5f9; 
                border-radius: 8px;
            }
            QLabel a {
                color: #4da6ff;
                text-decoration: underline;
            }
            QLabel a:hover {
                color: #66b3ff;
            }
        """
        )
        ffmpeg_layout.addWidget(guide_label)
        
        layout.addWidget(ffmpeg_group)
        
        
        # === App Updates Section ===
        app_update_group = QGroupBox(_("settings.app_updates_title"))
        app_update_layout = QVBoxLayout()

        self.app_updates_checkbox = QCheckBox(_("settings.check_app_updates"))
        self.app_updates_checkbox.setStyleSheet(checkbox_qss())
        app_update_layout.addWidget(self.app_updates_checkbox)
        
        self.beta_updates_checkbox = QCheckBox(_("settings.check_beta_updates"))
        self.beta_updates_checkbox.setStyleSheet(checkbox_qss())
        app_update_layout.addWidget(self.beta_updates_checkbox)
        
        app_update_group.setLayout(app_update_layout)
        layout.addWidget(app_update_group)
        
        # === yt-dlp Release Channel Section ===
        ytdlp_channel_group = QGroupBox(_("settings.ytdlp_channel"))
        ytdlp_channel_layout = QVBoxLayout()
        ytdlp_channel_layout.setSpacing(5)  # Reduce spacing
        ytdlp_channel_layout.setContentsMargins(10, 10, 10, 10)  # Reduce margins
        
        # Description
        channel_desc = QLabel(_("settings.ytdlp_channel_description"))
        channel_desc.setWordWrap(True)
        channel_desc.setStyleSheet("color: #64748b; font-size: 11px; padding: 2px;")
        ytdlp_channel_layout.addWidget(channel_desc)
        
        # Radio buttons for channel selection
        self.channel_stable_radio = QRadioButton(_("settings.ytdlp_channel_stable"))
        self.channel_nightly_radio = QRadioButton(_("settings.ytdlp_channel_nightly"))

        self.channel_stable_radio.setStyleSheet(radio_button_qss())
        self.channel_nightly_radio.setStyleSheet(radio_button_qss())
        
        # Connect radio button signals
        self.channel_stable_radio.toggled.connect(self._on_channel_changed)
        self.channel_nightly_radio.toggled.connect(self._on_channel_changed)
        
        ytdlp_channel_layout.addWidget(self.channel_stable_radio)
        ytdlp_channel_layout.addWidget(self.channel_nightly_radio)
        
        # Status label for channel operations
        self.channel_status_label = QLabel("")
        self.channel_status_label.setWordWrap(True)
        self.channel_status_label.setStyleSheet(
            "color: #64748b; font-size: 11px; padding: 5px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
        self.channel_status_label.setVisible(False)
        ytdlp_channel_layout.addWidget(self.channel_status_label)
        
        ytdlp_channel_group.setLayout(ytdlp_channel_layout)
        layout.addWidget(ytdlp_channel_group)
        
        # === Auto-Update yt-dlp Section ===
        auto_update_group_box = QGroupBox(_("settings.auto_update_ytdlp"))
        auto_update_layout = QVBoxLayout()

        # Enable/Disable auto-update checkbox
        self.auto_update_enabled = QCheckBox(_("settings.enable_auto_updates"))
        self.auto_update_enabled.setStyleSheet(checkbox_qss())
        auto_update_layout.addWidget(self.auto_update_enabled)

        # Frequency options
        frequency_label = QLabel(_("settings.update_frequency"))
        frequency_label.setStyleSheet("color: #0f172a; margin-top: 10px;")
        auto_update_layout.addWidget(frequency_label)

        self.startup_radio = QRadioButton(_("settings.check_startup"))
        self.daily_radio = QRadioButton(_("settings.check_daily"))
        self.weekly_radio = QRadioButton(_("settings.check_weekly"))

        self.startup_radio.setStyleSheet(radio_button_qss())
        self.daily_radio.setStyleSheet(self.startup_radio.styleSheet())
        self.weekly_radio.setStyleSheet(self.startup_radio.styleSheet())

        auto_update_layout.addWidget(self.startup_radio)
        auto_update_layout.addWidget(self.daily_radio)
        auto_update_layout.addWidget(self.weekly_radio)

        # Test update button
        test_update_layout = QHBoxLayout()
        test_update_button = QPushButton(_("settings.check_updates_now"))
        test_update_button.clicked.connect(self.test_update_check)
        test_update_button.setStyleSheet(primary_button_qss(min_width="120px"))
        test_update_layout.addWidget(test_update_button)
        test_update_layout.addStretch()
        auto_update_layout.addLayout(test_update_layout)

        auto_update_group_box.setLayout(auto_update_layout)
        layout.addWidget(auto_update_group_box)
        
        layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _load_auto_update_settings(self) -> None:
        """Load current auto-update settings for yt-dlp."""
        try:
            auto_settings = get_auto_update_settings()
            
            # Set checkbox
            self.auto_update_enabled.setChecked(auto_settings["enabled"])
            
            # Load beta setting
            beta_enabled = ConfigManager.get("check_beta_updates") or False
            self.beta_updates_checkbox.setChecked(beta_enabled)

            # Load app update checker setting (default enabled for older configs)
            app_updates_enabled = ConfigManager.get("check_app_updates")
            self.app_updates_checkbox.setChecked(app_updates_enabled is not False)
            
            # Set current selection based on saved settings
            current_frequency = auto_settings["frequency"]
            if current_frequency == "startup":
                self.startup_radio.setChecked(True)
            elif current_frequency == "daily":
                self.daily_radio.setChecked(True)
            else:  # weekly
                self.weekly_radio.setChecked(True)
            
            # Load channel setting
            channel = ConfigManager.get("ytdlp_channel")
            if channel is None:
                channel = "stable"  # Default to stable if not set
            
            if channel == "nightly":
                self.channel_nightly_radio.setChecked(True)
            else:
                self.channel_stable_radio.setChecked(True)
            
            # Update status label
            self._update_channel_status(channel)
            
        except Exception as e:
            logger.exception(f"Error loading auto-update settings: {e}")
    
    def get_auto_update_settings(self) -> tuple[bool, str]:
        """Returns the auto-update settings from the dialog."""
        enabled = self.auto_update_enabled.isChecked()

        if self.startup_radio.isChecked():
            frequency = "startup"
        elif self.daily_radio.isChecked():
            frequency = "daily"
        else:  # weekly_radio is checked
            frequency = "weekly"

        return enabled, frequency

    def get_beta_update_setting(self) -> bool:
        """Returns the beta update setting from the dialog."""
        return self.beta_updates_checkbox.isChecked()

    def get_app_update_checker_setting(self) -> bool:
        """Returns the app version checker setting from the dialog."""
        return self.app_updates_checkbox.isChecked()
    
    def _on_channel_changed(self, checked: bool) -> None:
        """Handle channel selection change."""
        if not checked:
            return
        
        # Determine which channel was selected
        new_channel = "nightly" if self.channel_nightly_radio.isChecked() else "stable"
        current_channel = ConfigManager.get("ytdlp_channel")
        if current_channel is None:
            current_channel = "stable"
        
        # If channel hasn't actually changed, just update status
        if new_channel == current_channel:
            self._update_channel_status(new_channel)
            return
        
        # Show switching message
        self.channel_status_label.setText(_("settings.ytdlp_switching_channel", channel=new_channel))
        self.channel_status_label.setStyleSheet(
            "color: #ffaa00; font-size: 11px; padding: 5px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
        self.channel_status_label.setVisible(True)
        
        # Disable radio buttons during switch
        self.channel_stable_radio.setEnabled(False)
        self.channel_nightly_radio.setEnabled(False)
        
        # Run channel switch in background thread
        def switch_channel():
            try:
                # Get yt-dlp path
                yt_dlp_path = get_yt_dlp_path()
                
                # Build the update command
                # When switching to stable from nightly, we need to get the latest stable version
                # to force the switch even if versions have the same date
                update_target = new_channel
                
                if new_channel == "stable" and current_channel == "nightly":
                    # Get the latest stable version tag from PyPI (no rate limiting)
                    logger.info("Fetching latest stable version tag from PyPI...")
                    try:
                        import requests
                        response = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=10)
                        response.raise_for_status()
                        latest_tag = response.json()["info"]["version"]
                        if latest_tag:
                            # PyPI returns version without zero-padding (e.g. "2026.2.21")
                            # but yt-dlp GitHub tags are zero-padded (e.g. "2026.02.21")
                            parts = latest_tag.split(".")
                            if len(parts) == 3:
                                latest_tag = f"{parts[0]}.{int(parts[1]):02d}.{int(parts[2]):02d}"
                            update_target = f"stable@{latest_tag}"
                            logger.info(f"Latest stable version tag: {latest_tag}")
                        else:
                            logger.warning("Could not determine latest stable tag, using 'stable'")
                    except Exception as e:
                        logger.warning(f"Failed to fetch latest stable tag, using 'stable': {e}")
                
                # Run the update-to command
                logger.info(f"Switching yt-dlp to {new_channel} channel...")
                logger.debug(f"Running command: {yt_dlp_path} --update-to {update_target}")
                result = subprocess.run(
                    [yt_dlp_path, "--update-to", update_target],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=SUBPROCESS_CREATIONFLAGS,
                )
                
                # Log the output for debugging
                if result.stdout:
                    logger.debug(f"yt-dlp stdout: {result.stdout.strip()}")
                if result.stderr:
                    logger.debug(f"yt-dlp stderr: {result.stderr.strip()}")
                logger.debug(f"yt-dlp return code: {result.returncode}")
                
                if result.returncode == 0:
                    # Success - save the preference
                    ConfigManager.set("ytdlp_channel", new_channel)
                    logger.info(f"Successfully switched to {new_channel} channel")
                    
                    # Update UI
                    self.channel_status_label.setText(_("settings.ytdlp_channel_switched", channel=new_channel))
                    self.channel_status_label.setStyleSheet(
                        "color: #00cc00; font-size: 11px; padding: 5px; "
                        "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
                    )
                    
                    # Make executable on Unix systems
                    if OS_NAME != "Windows":
                        import os
                        os.chmod(yt_dlp_path, 0o755)
                else:
                    # Failed - revert radio button
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip() if result.stdout else "Unknown error"
                    logger.error(f"Failed to switch channel: {error_msg}")
                    
                    self.channel_status_label.setText(_("settings.ytdlp_channel_switch_failed", error=error_msg))
                    self.channel_status_label.setStyleSheet(
                        "color: #ff6666; font-size: 11px; padding: 5px; "
                        "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
                    )
                    
                    # Revert radio selection
                    if current_channel == "nightly":
                        self.channel_nightly_radio.setChecked(True)
                    else:
                        self.channel_stable_radio.setChecked(True)
                        
            except subprocess.TimeoutExpired:
                logger.error("Channel switch timed out")
                self.channel_status_label.setText(_("settings.ytdlp_channel_switch_failed", error="Timeout"))
                self.channel_status_label.setStyleSheet(
                    "color: #ff6666; font-size: 11px; padding: 5px; "
                    "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
                )
                # Revert radio selection
                if current_channel == "nightly":
                    self.channel_nightly_radio.setChecked(True)
                else:
                    self.channel_stable_radio.setChecked(True)
                    
            except Exception as e:
                logger.exception(f"Error switching channel: {e}")
                self.channel_status_label.setText(_("settings.ytdlp_channel_switch_failed", error=str(e)))
                self.channel_status_label.setStyleSheet(
                    "color: #ff6666; font-size: 11px; padding: 5px; "
                    "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
                )
                # Revert radio selection
                if current_channel == "nightly":
                    self.channel_nightly_radio.setChecked(True)
                else:
                    self.channel_stable_radio.setChecked(True)
            finally:
                # Re-enable radio buttons
                self.channel_stable_radio.setEnabled(True)
                self.channel_nightly_radio.setEnabled(True)
        
        # Start the thread
        thread = threading.Thread(target=switch_channel, daemon=True)
        thread.start()
    
    def _update_channel_status(self, channel: str) -> None:
        """Update the channel status label."""
        self.channel_status_label.setText(_("settings.ytdlp_current_channel", channel=channel))
        self.channel_status_label.setStyleSheet(
            "color: #64748b; font-size: 11px; padding: 5px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
        self.channel_status_label.setVisible(True)
    
    def test_update_check(self) -> None:
        """Open the yt-dlp update dialog with proper progress tracking."""
        # Create and show the update dialog (non-modal to prevent blocking)
        dialog = YTDLPUpdateDialog(self)
        dialog.setModal(False)  # Make it non-modal
        dialog.show()  # Use show() instead of exec() to avoid blocking
    
    def check_for_updates(self) -> None:
        """Check FFmpeg version and compare with latest."""
        self.check_button.setEnabled(False)
        self.status_label.setText(_('ffmpeg_updater.status_checking'))
        self.status_label.setStyleSheet(
            "color: #ffaa00; font-size: 12px; padding: 8px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
        
        self.ffmpeg_check_thread = FFmpegCheckThread()
        self.ffmpeg_check_thread.finished.connect(self._on_ffmpeg_check_finished)
        self.ffmpeg_check_thread.error.connect(self._on_ffmpeg_check_error)
        self.ffmpeg_check_thread.start()

    @Slot(bool, str, str)
    def _on_ffmpeg_check_finished(self, update_available, current_version, latest_version):
        self.check_button.setEnabled(True)
        self._update_check_results(update_available, current_version, latest_version)

    @Slot(str)
    def _on_ffmpeg_check_error(self, error):
        self.check_button.setEnabled(True)
        self._show_check_error(error)
    
    def _update_check_results(self, update_available: bool, current_version: str, latest_version: str) -> None:
        """Handle completion of version check."""
        self.update_available = update_available
        self.current_version = current_version
        self.latest_version = latest_version
        
        # Update version labels
        self.current_version_label.setText(current_version)
        self.latest_version_label.setText(latest_version)
        
        # Update status
        if current_version == "Not installed":
            self.status_label.setText(_('ffmpeg_updater.status_not_installed'))
            self.status_label.setStyleSheet(
                "color: #ff6666; font-size: 12px; padding: 8px; "
                "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
            )
        elif update_available:
            self.status_label.setText(_('ffmpeg_updater.status_update_available'))
            self.status_label.setStyleSheet(
                "color: #ffaa00; font-size: 12px; padding: 8px; "
                "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
            )
        else:
            self.status_label.setText(_('ffmpeg_updater.status_up_to_date'))
            self.status_label.setStyleSheet(
                "color: #00cc00; font-size: 12px; padding: 8px; "
                "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
            )
    
    def _show_check_error(self, error: str) -> None:
        """Handle error during version check."""
        self.status_label.setText(_('ffmpeg_updater.check_failed'))
        self.status_label.setStyleSheet(
            "color: #ff6666; font-size: 12px; padding: 8px; "
            "background-color: #eff4fa; border-radius: 8px; margin: 5px 0;"
        )
