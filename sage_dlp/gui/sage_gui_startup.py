# -*- coding: utf-8 -*-
"""
Startup / lifecycle mixin for SageDLP GUI.

`StartupMixin` owns the post-UI-show bootstrap: silent background dependency
installation (FFmpeg + yt-dlp), the cookie bridge server, update checks
(application + yt-dlp auto-update), the update dialog, window-state
persistence, and the application close event cleanup.
"""

import webbrowser
from typing import TYPE_CHECKING

import markdown
from PySide6.QtCore import QByteArray, Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QStyle

from ..core.sage_utils import check_ffmpeg, should_check_for_auto_update
from ..core.sage_yt_dlp import get_yt_dlp_path, DownloadYtdlpThread
from ..core.sage_deno import check_deno_binary, DownloadDenoThread
from ..utils.sage_constants import ICON_PATH, SOUND_PATH
from ..utils.sage_config_manager import ConfigManager
from ..utils.sage_localization import _
from ..utils.sage_logger import logger
from .sage_gui_dialogs import AutoUpdateThread, FFmpegInstallThread
from .sage_gui_update_check import UpdateCheckThread
from .sage_stylesheet import StyleSheet

if TYPE_CHECKING:
    from .sage_gui_main import SageApp


class StartupMixin:
    """Application bootstrap, update checks, and close-event cleanup."""

    # ---- Window state -------------------------------------------------

    def _load_window_state(self: "SageApp") -> None:
        """Restore previous window geometry and state from config."""
        geo_b64 = ConfigManager.get("window_geometry")
        if geo_b64:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo_b64.encode("ascii")))
            except Exception:
                pass

        state_b64 = ConfigManager.get("window_state")
        if state_b64:
            try:
                self.restoreState(QByteArray.fromBase64(state_b64.encode("ascii")))
            except Exception:
                pass

    # ---- Startup checks ----------------------------------------------

    def _perform_startup_checks(self: "SageApp") -> None:
        """Perform potentially blocking startup checks after UI is shown."""

        # Silently install FFmpeg in background if missing
        if not check_ffmpeg():
            logger.info("FFmpeg not found — starting silent background installation")
            self._silent_ffmpeg_thread = FFmpegInstallThread()
            self._silent_ffmpeg_thread.finished.connect(self._on_silent_ffmpeg_finished)
            self._silent_ffmpeg_thread.start()

        # Silently download yt-dlp in background if missing
        ytdlp_path = get_yt_dlp_path()
        if ytdlp_path == "yt-dlp":  # Not found in app dir or PATH
            logger.info("yt-dlp not found — starting silent background download")
            self._silent_ytdlp_thread = DownloadYtdlpThread()
            self._silent_ytdlp_thread.finished_signal.connect(self._on_silent_ytdlp_finished)
            self._silent_ytdlp_thread.start()
        else:
            logger.info(f"Using yt-dlp from: {ytdlp_path}")

        # Silently install deno in background if missing (required for yt-dlp JS challenge solving)
        if not check_deno_binary():
            logger.info("deno not found — starting silent background download")
            self._silent_deno_thread = DownloadDenoThread()
            self._silent_deno_thread.finished_signal.connect(self._on_silent_deno_finished)
            self._silent_deno_thread.start()

        self.check_for_updates()

        # Start the cookie HTTP server for browser extension bridge
        if not self.cookie_server.start():
            logger.warning("Cookie bridge server could not be started — extension auto-import unavailable")

        # Check for auto-updates if enabled
        QTimer.singleShot(2000, self.check_auto_update_ytdlp) # Further delay auto-update check

    def play_notification_sound(self: "SageApp") -> None:
        """Play notification sound asynchronously (non-blocking)."""
        try:
            # Check if the notification sound file exists
            if not SOUND_PATH.exists():
                logger.warning(f"Notification sound file not found at: {SOUND_PATH}")
                return

            # Play the sound using QtMultimedia
            self.player.setSource(QUrl.fromLocalFile(str(SOUND_PATH)))
            self.player.play()
        except Exception as e:
            logger.exception(f"Error playing notification sound: {e}")

    # ---- Silent dependency install callbacks -------------------------

    def _on_silent_ffmpeg_finished(self: "SageApp", success: bool) -> None:
        """Called after silent FFmpeg installation completes."""
        if success:
            logger.info("FFmpeg silently installed successfully")
        else:
            logger.warning("Silent FFmpeg installation failed")
        if hasattr(self, "_silent_ffmpeg_thread"):
            try:
                self._silent_ffmpeg_thread.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            if self._silent_ffmpeg_thread.isRunning():
                self._silent_ffmpeg_thread.quit()
                self._silent_ffmpeg_thread.wait(1000)
            delattr(self, "_silent_ffmpeg_thread")

    def _on_silent_ytdlp_finished(self: "SageApp", success: bool, result: str) -> None:
        """Called after silent yt-dlp download completes."""
        if success:
            logger.info(f"yt-dlp silently downloaded to: {result}")
        else:
            logger.warning(f"Silent yt-dlp download failed: {result}")
        if hasattr(self, "_silent_ytdlp_thread"):
            try:
                self._silent_ytdlp_thread.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if self._silent_ytdlp_thread.isRunning():
                self._silent_ytdlp_thread.quit()
                self._silent_ytdlp_thread.wait(1000)
            delattr(self, "_silent_ytdlp_thread")

    def _on_silent_deno_finished(self: "SageApp", success: bool, result: str) -> None:
        """Called after silent deno download completes."""
        if success:
            logger.info(f"deno silently installed to: {result}")
        else:
            logger.warning(f"Silent deno download failed: {result}")
        if hasattr(self, "_silent_deno_thread"):
            try:
                self._silent_deno_thread.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
            if self._silent_deno_thread.isRunning():
                self._silent_deno_thread.quit()
                self._silent_deno_thread.wait(1000)
            delattr(self, "_silent_deno_thread")

    # ---- Application update checks -----------------------------------

    def check_for_updates(self: "SageApp") -> None:
        """Starts the update check in a background thread."""
        if ConfigManager.get("check_app_updates") is False:
            logger.info("App version checker is disabled in settings.")
            return

        self.update_thread = UpdateCheckThread(self.version)
        self.update_thread.update_available.connect(self.show_update_dialog)
        self.update_thread.start()

    def show_update_dialog(self: "SageApp", latest_version, release_url, changelog) -> None:
        msg = QDialog(self)
        msg.setWindowTitle(_("update_dialog.title"))
        msg.setMinimumWidth(600)  # Increased width for better layout
        msg.setMinimumHeight(450)  # Increased height for better spacing

        # Set custom icon directly
        try:
            if self.windowIcon() and not self.windowIcon().isNull():
                msg.setWindowIcon(self.windowIcon())
            else:
                # Fallback to icon file
                if ICON_PATH.exists():
                    msg.setWindowIcon(QIcon(str(ICON_PATH)))
        except Exception:
            pass

        layout = QVBoxLayout(msg)
        layout.setSpacing(15)  # Increased spacing for better layout
        layout.setContentsMargins(20, 20, 20, 20)  # Added margins

        # Header with icon and title
        header_layout = QHBoxLayout()

        # Add update icon
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload).pixmap(32, 32))
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(f"<h2 style='color: #2a4a82; margin: 0;'>{_('update_dialog.title')}</h2>")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Update message with better formatting
        message_label = QLabel(
            f"<div style='font-size: 13px; line-height: 1.4;'>"
            f"<b style='color: #0f172a;'>{_('update_dialog.new_version_available')}</b><br><br>"
            f"<span style='color: #64748b;'>{_('update_dialog.current_version_label')} <b style='color: #0f172a;'>{self.version}</b></span><br>"
            f"<span style='color: #64748b;'>{_('update_dialog.latest_version_label')} <b style='color: #059669;'>{latest_version}</b></span>"
            f"</div>"
        )
        message_label.setWordWrap(True)
        message_label.setStyleSheet(StyleSheet.UPDATE_DIALOG_MESSAGE)
        layout.addWidget(message_label)

        # Changelog Section
        changelog_label = QLabel(f"<b style='color: #0f172a; font-size: 14px;'>{_('update_dialog.changelog')}:</b>")
        changelog_label.setStyleSheet("padding: 5px 0; margin-top: 10px;")
        layout.addWidget(changelog_label)

        changelog_text = QTextEdit()
        changelog_text.setReadOnly(True)
        # Convert Markdown to HTML and set it
        try:
            html_changelog = markdown.markdown(
                changelog,
                extensions=[
                    "markdown.extensions.tables",
                    "markdown.extensions.fenced_code",
                ],
            )
            changelog_text.setHtml(html_changelog)
        except Exception as e:
            logger.warning(f"Error converting changelog markdown to HTML: {e}", exc_info=True)
            changelog_text.setPlainText(changelog)  # Fallback to plain text

        changelog_text.setStyleSheet(StyleSheet.UPDATE_DIALOG_CHANGELOG)
        changelog_text.setMaximumHeight(180)  # Limit height
        layout.addWidget(changelog_text)

        # Buttons with better styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        download_btn = QPushButton(_('update_dialog.download_update'))
        download_btn.clicked.connect(lambda: self.open_release_page(release_url))
        download_btn.setStyleSheet(StyleSheet.UPDATE_DIALOG_DOWNLOAD_BTN)

        remind_btn = QPushButton(_('update_dialog.remind_later'))
        remind_btn.clicked.connect(msg.close)
        remind_btn.setStyleSheet(StyleSheet.UPDATE_DIALOG_REMIND_BTN)

        button_layout.addStretch()
        button_layout.addWidget(download_btn)
        button_layout.addWidget(remind_btn)
        layout.addLayout(button_layout)

        # Style the dialog with improved theme matching
        msg.setStyleSheet(StyleSheet.UPDATE_DIALOG_MAIN)

        self.run_dialog_with_blur(msg)

    def open_release_page(self: "SageApp", url) -> None:
        webbrowser.open(url)

    # ---- yt-dlp auto-update ------------------------------------------

    def check_auto_update_ytdlp(self: "SageApp") -> None:
        """Check and perform auto-update for yt-dlp if enabled and due."""
        try:
            # Check if auto-update should be performed
            if should_check_for_auto_update():
                logger.info("Performing auto-update check for yt-dlp...")
                # Perform the auto-update in a non-blocking way
                # We don't want to block the UI startup for this
                QTimer.singleShot(2000, self._perform_auto_update)  # Delay 2 seconds after startup
        except Exception as e:
            logger.exception(f"Error in auto-update check: {e}")

    def _perform_auto_update(self: "SageApp") -> None:
        """Actually perform the auto-update check and update if needed in a background thread."""
        # Check if a download is currently running or analysis is in progress
        if (self.current_download and self.current_download.isRunning()) or self.is_analyzing:
            logger.info("Download or analysis in progress, skipping auto-update check.")
            return

        try:
            self.is_updating_ytdlp = True  # Set flag
            # Create and start the auto-update thread to avoid blocking the UI

            self.auto_update_thread = AutoUpdateThread()
            self.auto_update_thread.update_finished.connect(self._on_auto_update_finished)
            self.auto_update_thread.start()
        except Exception as e:
            self.is_updating_ytdlp = False  # Reset flag on error
            logger.exception(f"Error starting auto-update thread: {e}")

    def _on_auto_update_finished(self: "SageApp", success, message) -> None:
        self.is_updating_ytdlp = False  # Reset flag
        """Handle auto-update completion."""
        if success:
            logger.info(f"Auto-update completed successfully: {message}")
        else:
            logger.warning(f"Auto-update completed with issues: {message}")

        # Clean up the thread reference and ensure it's properly finished
        if hasattr(self, "auto_update_thread"):
            # Disconnect all signals to prevent further callbacks
            self.auto_update_thread.update_finished.disconnect()
            # Make sure thread is finished
            if self.auto_update_thread.isRunning():
                self.auto_update_thread.quit()
                self.auto_update_thread.wait(1000)  # Wait up to 1 second
            # Remove the reference
            delattr(self, "auto_update_thread")

    # ---- Close event -------------------------------------------------

    def closeEvent(self: "SageApp", event) -> None:
        """Handle application close event to ensure proper cleanup of background threads."""
        try:
            # Stop the analysis thread if it's running
            if hasattr(self, "_analysis_thread") and self._analysis_thread is not None and self._analysis_thread.isRunning():
                logger.info("Stopping analysis thread...")
                self._analysis_thread.cancel()
                if not self._analysis_thread.wait(2000):  # Wait up to 2 seconds
                    logger.warning("Force terminating analysis thread...")
                    self._analysis_thread.terminate()
                    self._analysis_thread.wait(1000)

            # Stop the auto-update thread if it's running
            if hasattr(self, "auto_update_thread") and self.auto_update_thread.isRunning():
                logger.info("Stopping auto-update thread...")
                self.auto_update_thread.quit()
                if not self.auto_update_thread.wait(3000):  # Wait up to 3 seconds for graceful shutdown
                    logger.warning("Force terminating auto-update thread...")
                    self.auto_update_thread.terminate()
                    self.auto_update_thread.wait(1000)  # Wait for termination

            # Cancel any running downloads
            if self.current_download and self.current_download.isRunning():
                logger.info("Canceling running download...")
                self.current_download.cancel()
                if not self.current_download.wait(3000):  # Wait up to 3 seconds for graceful shutdown
                    logger.warning("Force terminating download thread...")
                    self.current_download.terminate()
                    self.current_download.wait(1000)  # Wait for termination

            # Stop silent install threads
            for thread_attr in ["_silent_ffmpeg_thread", "_silent_ytdlp_thread", "_silent_deno_thread"]:
                thread = getattr(self, thread_attr, None)
                if thread is not None and thread.isRunning():
                    logger.info(f"Stopping {thread_attr}...")
                    if not thread.wait(2000):
                        thread.terminate()
                        thread.wait(1000)

            # Stop the cookie bridge server
            if hasattr(self, "cookie_server"):
                self.cookie_server.stop()

            # Save the window size and state
            try:
                ConfigManager.set("window_geometry", self.saveGeometry().toBase64().data().decode("ascii"))
                ConfigManager.set("window_state", self.saveState().toBase64().data().decode("ascii"))
            except Exception:
                pass

            logger.info("Application closing...")
            event.accept()
        except Exception as e:
            logger.exception(f"Error during application close: {e}")
            event.accept()  # Accept the close event anyway
