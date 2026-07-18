# -*- coding: utf-8 -*-
"""
Dialog-launcher and playlist-ops mixin for SageDLP GUI.

`DialogOpsMixin` hosts the modal dialog launchers (download settings, custom
options, playlist selection), playlist save-to-file, and the cookie bridge
slots (`_on_cookies_received_from_extension`, plus the cookie-config
initializer called from `SageApp.__init__`).
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..core.sage_utils import save_path
from ..utils.sage_config_manager import ConfigManager
from ..utils.sage_localization import _
from ..utils.sage_logger import logger
from .sage_gui_dialogs import (
    CustomOptionsDialog,
    DownloadSettingsDialog,
    PlaylistSelectionDialog,
)

if TYPE_CHECKING:
    from .sage_gui_main import SageApp


class DialogOpsMixin:
    """Modal dialog launchers, playlist save, and cookie bridge slots."""

    def _initialize_cookie_settings_from_config(self: "SageApp") -> None:
        """Initialize cookie settings and restore from last session if active."""
        self.cookie_file_path = None
        self.browser_cookies_option = None

        # Check if the user wants to remember cookies across sessions
        remember_val = ConfigManager.get("cookie_remember")
        should_remember = True if remember_val is None else remember_val

        if ConfigManager.get("cookie_active") and should_remember:
            source = ConfigManager.get("cookie_source")
            if source == "file":
                saved_path = ConfigManager.get("cookie_file_path")
                if saved_path and Path(saved_path).exists():
                    self.cookie_file_path = Path(saved_path)
                    logger.info(f"Restored cookie file from previous session: {self.cookie_file_path}")
            elif source == "browser":
                browser = ConfigManager.get("cookie_browser")
                profile = ConfigManager.get("cookie_browser_profile")
                if browser:
                    self.browser_cookies_option = f"{browser}:{profile}" if profile else browser
                    logger.info(f"Restored browser cookies from previous session: {self.browser_cookies_option}")
        else:
            # Revert activation back if the user opted NOT to remember them
            ConfigManager.set("cookie_active", False)

    def show_download_settings_dialog(self: "SageApp") -> None:  # Renamed method
        dialog = DownloadSettingsDialog(self.last_path, self.speed_limit_value, self.speed_limit_unit_index, self)
        if self.run_dialog_with_blur(dialog):
            # Update Path
            new_path = dialog.get_selected_path()
            path_changed = False
            if new_path != self.last_path:
                self.last_path = new_path
                save_path(self, self.last_path)  # Save the updated path
                path_changed = True
                logger.info(f"Download path updated to: {self.last_path}")

            # Update Speed Limit
            new_limit_value = dialog.get_selected_speed_limit()
            new_unit_index = dialog.get_selected_unit_index()
            limit_changed = False
            if new_limit_value != self.speed_limit_value or new_unit_index != self.speed_limit_unit_index:
                self.speed_limit_value = new_limit_value
                self.speed_limit_unit_index = new_unit_index
                limit_changed = True
                logger.info(
                    f"Speed limit updated to: {self.speed_limit_value} {['KB/s', 'MB/s'][self.speed_limit_unit_index] if self.speed_limit_value else 'None'}"
                )
                # Save speed limit settings to config
                ConfigManager.set("speed_limit_value", self.speed_limit_value)
                ConfigManager.set("speed_limit_unit_index", self.speed_limit_unit_index)

            # Update Output Format Settings
            new_force_format = dialog.get_force_format_enabled()
            new_preferred_format = dialog.get_preferred_format()
            format_changed = False
            if new_force_format != self.force_output_format or new_preferred_format != self.preferred_output_format:
                self.force_output_format = new_force_format
                self.preferred_output_format = new_preferred_format
                format_changed = True
                logger.info(f"Output format settings updated - Force: {self.force_output_format}, Preferred: {self.preferred_output_format}")

            # Update Audio Format Settings
            new_force_audio_format = dialog.get_force_audio_format_enabled()
            new_preferred_audio_format = dialog.get_preferred_format()
            new_audio_normalization = dialog.get_audio_normalization_enabled()
            audio_format_changed = False
            if (new_force_audio_format != self.force_audio_format or
                new_preferred_audio_format != self.preferred_audio_format or
                new_audio_normalization != self.audio_normalization):
                self.force_audio_format = new_force_audio_format
                self.preferred_audio_format = new_preferred_audio_format
                self.audio_normalization = new_audio_normalization
                audio_format_changed = True
                logger.info(f"Audio format settings updated - Force: {self.force_audio_format}, Preferred: {self.preferred_audio_format}, Norm: {self.audio_normalization}")

            # Update Generic Mode Setting
            new_generic_mode = dialog.get_generic_mode_enabled()
            generic_mode_changed = False
            if new_generic_mode != self.generic_mode_enabled:
                self.generic_mode_enabled = new_generic_mode
                generic_mode_changed = True
                self._update_url_placeholder()
                logger.info(f"Generic mode updated - Enabled: {self.generic_mode_enabled}")

            # Update Tooltip if anything changed
            if path_changed or limit_changed or format_changed or audio_format_changed or generic_mode_changed:
                self._update_settings_tooltip()

    def show_custom_options(self: "SageApp") -> None:
        dialog = CustomOptionsDialog(self)
        if self.run_dialog_with_blur(dialog):
            # Handle proxy options
            proxy_url = dialog.get_proxy_url()
            geo_proxy_url = dialog.get_geo_proxy_url()

            # Update instance variables
            self.proxy_url = proxy_url
            self.geo_proxy_url = geo_proxy_url

            # Save proxy settings to config
            ConfigManager.set("proxy_url", proxy_url)
            ConfigManager.set("geo_proxy_url", geo_proxy_url)

            # Show confirmation messages
            if proxy_url:
                logger.info(f"Main proxy set: {self.proxy_url}")
                QMessageBox.information(
                    self,
                    _("proxy.set_title"),
                    _("proxy.set_message", proxy=proxy_url),
                )

            if geo_proxy_url:
                logger.info(f"Geo-verification proxy set: {self.geo_proxy_url}")
                QMessageBox.information(
                    self,
                    _("proxy.geo_set_title"),
                    _("proxy.geo_set_message", proxy=geo_proxy_url),
                )

            # Show a combined message if both are cleared
            if not proxy_url and not geo_proxy_url and (ConfigManager.get("proxy_url") or ConfigManager.get("geo_proxy_url")):
                QMessageBox.information(
                    self,
                    _("proxy.cleared_title"),
                    _("proxy.cleared_message"),
                )

    def open_playlist_selection_dialog(self: "SageApp") -> None:
        if not self.is_playlist or not self.playlist_entries:
            logger.info("No playlist data available to select from.")
            return

        dialog = PlaylistSelectionDialog(self.playlist_entries, self.selected_playlist_items, self)

        if self.run_dialog_with_blur(dialog):
            self.selected_playlist_items = dialog.get_selected_items_string()
            logger.info(f"Playlist items selected: {self.selected_playlist_items}")

            # Update button text (this call is safe as it happens in the main thread after dialog closes)
            if self.selected_playlist_items is None:
                button_text = "Select Videos... (All selected)"
            else:
                selected_indices = dialog._parse_selection_string(self.selected_playlist_items)
                count = len(selected_indices)
                display_text = (
                    self.selected_playlist_items if len(self.selected_playlist_items) < 30 else f"{count} videos selected"
                )
                button_text = f"Select Videos... ({display_text})"
            self.playlist_select_btn.setText(button_text)  # Direct call is fine here

    def save_playlist_to_file(self: "SageApp") -> None:
        """Save current playlist URLs/info to a file."""
        if not getattr(self, "playlist_entries", None):
            QMessageBox.warning(self, _("playlist.save_error_title"), _("playlist.no_videos_to_save"))
            return

        default_dir = str(Path(self.last_path) / "playlist.txt")
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            _("playlist.save_as"),
            default_dir,
            "Text files (*.txt);;M3U playlists (*.m3u);;CSV files (*.csv);;JSON files (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if "Text files" in selected_filter:
                    for index, entry in enumerate(self.playlist_entries):
                        duration = entry.get("duration")
                        duration_str = ""
                        if duration:
                            try:
                                m, s = divmod(int(duration), 60)
                                h, m = divmod(m, 60)
                                if h > 0:
                                    duration_str = f" [{h}:{m:02d}:{s:02d}]"
                                else:
                                    duration_str = f" [{m:02d}:{s:02d}]"
                            except (ValueError, TypeError):
                                pass

                        title = entry.get('title', f'Video {index + 1}')
                        # Formatting output to include index and duration
                        f.write(f"{index + 1}. {title}{duration_str} - {entry.get('url', '')}\n")
                elif "M3U" in selected_filter:
                    f.write("#EXTM3U\n")
                    for entry in self.playlist_entries:
                        duration = int(entry.get('duration', 0)) if entry.get('duration') else 0
                        title = entry.get('title', 'Unknown Title')
                        f.write(f"#EXTINF:{duration},{title}\n{entry.get('url', '')}\n")
                elif "CSV" in selected_filter:
                    import csv
                    writer = csv.writer(f, lineterminator='\n')
                    # Adding Playlist Index to CSV and formatting Title with index and duration
                    writer.writerow(['Playlist Index', 'Title', 'URL', 'Duration', 'Uploader'])
                    for index, entry in enumerate(self.playlist_entries):
                        duration = entry.get("duration")
                        duration_str = ""
                        if duration:
                            try:
                                m, s = divmod(int(duration), 60)
                                h, m = divmod(m, 60)
                                if h > 0:
                                    duration_str = f" [{h}:{m:02d}:{s:02d}]"
                                else:
                                    duration_str = f" [{m:02d}:{s:02d}]"
                            except (ValueError, TypeError):
                                pass

                        title = entry.get('title', f'Video {index + 1}')
                        formatted_title = f"{index + 1}. {title}{duration_str}"
                        writer.writerow([index + 1, formatted_title, entry.get('url', ''), entry.get('duration', ''), entry.get('uploader', '')])
                elif "JSON" in selected_filter:
                    import json
                    json.dump(self.playlist_entries, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, _("playlist.save_success_title"), _("playlist.saved_successfully"))
        except Exception as e:
            logger.exception(f"Error saving playlist: {e}")
            QMessageBox.critical(self, _("playlist.save_error_title"), _("playlist.save_error_msg"))

    def _on_cookies_received_from_extension(self: "SageApp", cookie_file: str, url: str) -> None:
        """
        Called when the browser extension POSTs cookies to our local server.
        Automatically sets the cookie file path and activates it.
        """
        path = Path(cookie_file)
        if not path.exists():
            return

        self.cookie_file_path = path
        self.browser_cookies_option = None  # Clear browser-based cookies
        ConfigManager.set("cookie_active", True)
        ConfigManager.set("cookie_source", "file")
        ConfigManager.set("cookie_file_path", str(path))
        logger.info(f"Auto-imported cookies from extension: {path.name} (for {url})")

        # Update the status indicator in the cookie dialog if it's open
        # (no-op if not visible, since the dialog re-reads status on open)
