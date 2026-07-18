# -*- coding: utf-8 -*-
"""
Download lifecycle mixin for SageDLP GUI.

`DownloadMixin` owns the download flow: starting a `DownloadThread`, reacting
to its progress / status / completion / error signals, managing the pause /
cancel / open-folder controls, and recording finished downloads to history.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPropertyAnimation, Slot
from PySide6.QtWidgets import QCheckBox, QMessageBox

from ..core.sage_downloader import DownloadThread
from ..core.sage_utils import validate_video_url
from ..utils.sage_config_manager import ConfigManager
from ..utils.sage_constants import (
    AUDIO_EXTENSIONS,
    SUBPROCESS_CREATIONFLAGS,
    SUBTITLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from ..utils.sage_history_manager import HistoryManager
from ..utils.sage_localization import _
from ..utils.sage_logger import logger
from .sage_stylesheet import StyleSheet

if TYPE_CHECKING:
    from .sage_gui_main import SageApp


class DownloadMixin:
    """Download orchestration: start, progress, completion, pause/cancel."""

    def start_download(self: "SageApp") -> None:
        if self.is_updating_ytdlp:
            QMessageBox.warning(self, _("update.update_in_progress_title"), _("update.update_in_progress_message"))
            return

        url = self.url_input.text().strip()
        # --- Use self.last_path instead of reading from QLineEdit ---
        path = self.last_path

        if not url or not path:
            # More specific error message if path is missing
            if not path:
                self.set_status_message_animated(_('download.please_set_path'))
                self.animate_widget_shake(self.settings_button)
            elif not url:
                self.set_status_message_animated(_('download.please_enter_url'))
                self.animate_widget_shake(self.url_input)
            else:
                self.set_status_message_animated(_('download.please_enter_url_and_path'))
                self.animate_widget_shake(self.url_input)
                self.animate_widget_shake(self.settings_button)
            return
        # --- End Path Change ---

        # Validate URL before starting download
        is_valid, error_message = validate_video_url(url, generic_mode=self.generic_mode_enabled)
        if not is_valid:
            QMessageBox.warning(self, _("main_ui.error_title"), error_message)
            self.animate_widget_shake(self.url_input)
            return

        # Subtitle-only mode: 只下载带单词级时间戳的字幕并生成精确断句 SRT
        is_subtitle_only = hasattr(self, "subtitle_only_button") and self.subtitle_only_button.isChecked()
        logger.info(f"[Download] start. url={url} path={path} is_subtitle_only={is_subtitle_only}")
        if is_subtitle_only:
            selected_subs = self.selected_subtitles if hasattr(self, "selected_subtitles") else []
            if not selected_subs:
                logger.warning("[Download] subtitle-only mode but no subtitle selected")
                self.set_status_message_animated(_('main_ui.subtitle_only_require_subs'))
                self.animate_widget_shake(self.subtitle_select_btn)
                return
            # 仅字幕模式不需要选择视频/音频格式
            format_id = ""
            is_audio_only = False
            format_has_audio = False
            logger.info(f"[Download] subtitle-only selected_subs={selected_subs}")
        else:
            # Get selected format
            selected_format = self.get_selected_format()
            if not selected_format:
                self.set_status_message_animated(_('download.please_select_format'))
                self.animate_widget_shake(self.format_table)
                return
            format_id = selected_format["format_id"]
            is_audio_only = bool(selected_format.get("is_audio_only"))
            format_has_audio = bool(selected_format.get("has_audio"))

        # Show preparation message
        self.status_label.setText(_('download.preparing'))
        self.progress_bar.setValue(0)  # Reset progress (range is 0-10000)
        self.open_folder_btn.setVisible(False)  # Hide the open folder button on new download

        # Get resolution for filename
        resolution = "default"
        for row in range(self.format_table.rowCount()):
            cell_widget = self.format_table.cellWidget(row, 0)
            if cell_widget:
                cb = cell_widget.layout().itemAt(0).widget()
                if isinstance(cb, QCheckBox) and cb.isChecked():
                    if self.is_playlist:
                        res_item = self.format_table.item(row, 2)
                    else:
                        res_item = self.format_table.item(row, 3)

                    if res_item and res_item.text() != "N/A":
                        resolution = res_item.text().replace("≤ ", "").strip()
                    break

        # Get subtitle selection if available - Now get the list
        selected_subs = self.selected_subtitles if hasattr(self, "selected_subtitles") else []

        # Get playlist selection IF in playlist mode - USE STORED VALUE
        playlist_items_to_download = None
        if self.is_playlist:
            playlist_items_to_download = self.selected_playlist_items  # Use the stored selection string

        # --- Use stored speed limit values ---
        rate_limit = None
        if self.speed_limit_value:
            try:
                limit_value = float(self.speed_limit_value)
                if self.speed_limit_unit_index == 0:  # KB/s
                    rate_limit = f"{int(limit_value * 1024)}"
                elif self.speed_limit_unit_index == 1:  # MB/s
                    rate_limit = f"{int(limit_value * 1024 * 1024)}"
            except ValueError:
                # Use a signal to show error in status bar, similar to URL/Path errors
                self.signals.update_status.emit(_("errors.invalid_speed_limit"))
                return
        # --- End speed limit update ---

        # Save thumbnail if enabled
        if self.save_thumbnail:
            # Consider moving thumbnail download *after* successful video download
            # Or handle errors more gracefully if thumbnail download fails
            try:
                self.download_thumbnail_file(url, path)
            except Exception as e:
                logger.warning(f"Thumbnail download failed: {e}", exc_info=True)
                # Optionally inform the user, but don't stop the main download

        # Get filename format from config
        filename_format = ConfigManager.get("filename_format")
        concurrent_fragments = ConfigManager.get("concurrent_fragments") or 1

        # Create download thread with resolution in output template
        self.download_thread = DownloadThread(
            url=url,
            path=path,
            format_id=format_id,
            is_audio_only=is_audio_only,
            format_has_audio=format_has_audio,
            subtitle_langs=selected_subs,  # Pass the list of selected subs
            is_playlist=self.is_playlist,  # Use the flag directly
            merge_subs=self.merge_subs_checkbox.isChecked(),
            resolution=resolution,
            playlist_items=playlist_items_to_download,  # Pass the selection string
            save_description=self.save_description,  # Pass the new flag here
            embed_chapters=self.embed_chapters,  # Pass the embed chapters flag
            cookie_file=self.cookie_file_path,  # Pass the cookie file path
            browser_cookies=self.browser_cookies_option,  # Pass the browser cookies option
            rate_limit=rate_limit,  # Pass the calculated rate limit
            download_section=self.download_section,  # Pass the download section
            force_keyframes=self.force_keyframes,  # Pass the force keyframes setting
            proxy_url=self.proxy_url,  # Pass the proxy URL
            subtitle_only_mode=is_subtitle_only,  # 仅字幕模式标志
            geo_proxy_url=self.geo_proxy_url,  # Pass the geo-verification proxy URL
            force_output_format=self.force_output_format,  # Pass force output format setting
            preferred_output_format=self.preferred_output_format,  # Pass preferred format
            force_audio_format=self.force_audio_format,  # Pass force audio format setting
            preferred_audio_format=self.preferred_audio_format,  # Pass preferred audio format
            audio_normalization=self.audio_normalization,  # Pass audio normalization setting
            filename_format=filename_format,  # Pass the filename format
            concurrent_fragments=concurrent_fragments, # Pass the concurrent fragments
        )

        # Connect signals
        self.download_thread.progress_signal.connect(self.update_progress_bar)
        self.download_thread.status_signal.connect(self.set_status_message_animated)
        self.download_thread.update_details.connect(self.download_details_label.setText)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)
        self.download_thread.file_exists_signal.connect(self.file_already_exists)

        # 字幕断句 pipeline：只要选了字幕就自动走断句（不再需要勾选 LLM 复选框）
        # LLM 复选框的含义变为"是否使用 LLM 模式"（rule 模式为默认，无需外部服务）
        has_subs = bool(selected_subs)
        self.download_thread.llm_segment_enabled = has_subs or is_subtitle_only
        if self.download_thread.llm_segment_enabled:
            # LLM 复选框勾选 → 用 llm 模式（需配置 LLM 服务）；未勾选 → 用 rule 模式（纯规则）
            llm_mode = "llm" if (hasattr(self, "llm_segment_checkbox") and self.llm_segment_checkbox.isChecked()) else "rule"
            llm_config = {
                "mode": llm_mode,
                "url": ConfigManager.get("llm_url") or "http://localhost:8000",
                "api_key": ConfigManager.get("llm_api_key") or "",
                "model": ConfigManager.get("llm_model") or "gpt-4.1",
                "temperature": ConfigManager.get("llm_temperature") or 0.1,
                "max_workers": ConfigManager.get("llm_max_workers") or 10,
                "timeout": ConfigManager.get("llm_timeout") or 60,
                "max_retries": ConfigManager.get("llm_max_retries") or 3,
                "segmentation_params": {
                    "SOFT_LIMIT": ConfigManager.get("llm_segmentation_soft_limit") or 70,
                    "HARD_LIMIT": ConfigManager.get("llm_segmentation_hard_limit") or 85,
                    "TARGET_CPS": ConfigManager.get("llm_segmentation_target_cps") or 14,
                    "LIMIT_CPS": ConfigManager.get("llm_segmentation_limit_cps") or 18,
                }
            }
            self.download_thread.llm_config = llm_config
            logger.info(f"[Download] 字幕断句 pipeline 已启用，模式: {llm_mode}")

        # Reset download state
        self.download_paused = False
        self.download_cancelled = False

        # Show pause/cancel buttons
        self.pause_btn.setText(_("buttons.pause"))
        self.animate_widget_fade_in(self.pause_btn)
        self.animate_widget_fade_in(self.cancel_btn)

        # Start download thread
        self.current_download = self.download_thread
        self.download_thread.start()
        self.toggle_download_controls(False)

    def download_finished(self: "SageApp") -> None:
        self.toggle_download_controls(True)
        self.animate_widget_fade_out(self.pause_btn)
        self.animate_widget_fade_out(self.cancel_btn)
        self.progress_bar.setValue(10000)  # 100% in 0-10000 range

        # 仅字幕模式：LLM 断言已完成并发出了带 SRT 路径的完成消息，这里不再覆盖
        is_subtitle_only = getattr(self.download_thread, "subtitle_only_mode", False) if self.download_thread else False

        # Set completion message based on the file type of last downloaded file
        if self.download_thread and self.download_thread.current_filename:
            filename = Path(self.download_thread.current_filename)
            ext = filename.suffix.lower()

            # 仅字幕模式：current_filename 指向最后生成的 SRT，不重复发"字幕下载完成"
            if not is_subtitle_only:
                # Video file extensions
                if ext in VIDEO_EXTENSIONS:
                    self.set_status_message_animated(_('download.video_completed'))
                # Audio file extensions
                elif ext in AUDIO_EXTENSIONS:
                    self.set_status_message_animated(_('download.audio_completed'))
                # Subtitle file extensions
                elif ext in SUBTITLE_EXTENSIONS:
                    self.set_status_message_animated(_('download.subtitle_completed'))
                # Default case
                else:
                    self.set_status_message_animated(_('download.completed'))

            # Show the open folder button
            self.animate_widget_fade_in(self.open_folder_btn)

            # Save to history
            try:
                if self.download_thread.last_file_path and self.video_info:
                    # Get video information
                    title = self.video_info.get("title", _("video_info.unknown_title"))
                    channel = self.video_info.get("channel", None) or self.video_info.get("uploader", None)
                    duration = self.video_info.get("duration_string", None)

                    # Prepare download options
                    download_options = {
                        "format_id": self.download_thread.format_id,
                        "subtitle_langs": self.download_thread.subtitle_langs,
                        "merge_subs": self.download_thread.merge_subs,
                        "save_description": self.download_thread.save_description,
                        "embed_chapters": self.download_thread.embed_chapters,
                        "download_section": self.download_thread.download_section,
                        "force_keyframes": self.download_thread.force_keyframes,
                    }

                    # Add to history
                    HistoryManager.add_entry(
                        title=title,
                        url=self.video_url,
                        thumbnail_url=self.thumbnail_url,
                        file_path=str(self.download_thread.last_file_path),
                        format_id=self.download_thread.format_id,
                        is_audio_only=self.download_thread.is_audio_only,
                        resolution=self.download_thread.resolution,
                        channel=channel,
                        duration=duration,
                        download_options=download_options,
                    )
                    logger.info(f"Added download to history: {title}")
            except Exception as e:
                logger.error(f"Error saving to history: {e}", exc_info=True)

        # Play notification sound when download completes
        self.play_notification_sound()

    def open_download_folder(self: "SageApp") -> None:
        """Open the folder containing the downloaded file and select it if possible"""
        try:
            if self.download_thread and self.download_thread.last_file_path:
                file_path = Path(self.download_thread.last_file_path)

                if file_path.exists():
                    # On Windows, use explorer with /select to highlight the file
                    if subprocess.sys.platform == "win32":
                        subprocess.run(['explorer', '/select,', str(file_path)], creationflags=SUBPROCESS_CREATIONFLAGS)
                    # On macOS, use open with -R to reveal in Finder
                    elif subprocess.sys.platform == "darwin":
                        subprocess.run(['open', '-R', str(file_path)])
                    # On Linux, try to open the folder (file selection not widely supported)
                    else:
                        folder_path = file_path.parent
                        subprocess.run(['xdg-open', str(folder_path)])

                    logger.info(f"Opened folder for: {file_path}")
                else:
                    # If file doesn't exist, just open the download folder
                    folder_path = Path(self.last_path)
                    if folder_path.exists():
                        if subprocess.sys.platform == "win32":
                            subprocess.run(['explorer', str(folder_path)], creationflags=SUBPROCESS_CREATIONFLAGS)
                        elif subprocess.sys.platform == "darwin":
                            subprocess.run(['open', str(folder_path)])
                        else:
                            subprocess.run(['xdg-open', str(folder_path)])
                    else:
                        logger.warning(f"Download folder does not exist: {folder_path}")
            else:
                # Fallback to opening the general download folder
                folder_path = Path(self.last_path)
                if folder_path.exists():
                    if subprocess.sys.platform == "win32":
                        subprocess.run(['explorer', str(folder_path)], creationflags=SUBPROCESS_CREATIONFLAGS)
                    elif subprocess.sys.platform == "darwin":
                        subprocess.run(['open', str(folder_path)])
                    else:
                        subprocess.run(['xdg-open', str(folder_path)])
                else:
                    logger.warning(f"Download folder does not exist: {folder_path}")

        except Exception as e:
            logger.exception(f"Error opening download folder: {e}")
            QMessageBox.warning(self, _("main_ui.error_title"), _("main_ui.open_folder_error", error=str(e)))

    def download_error(self: "SageApp", error_message) -> None:
        self.toggle_download_controls(True)
        self.pause_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.status_label.setText(_("errors.generic_error", error=error_message))
        self.download_details_label.setText("")  # Clear details label on error

    def update_progress_bar(self: "SageApp", value) -> None:
        try:
            # Scale float percentage (0-100) to progress bar range (0-10000) for precision
            scaled_value = int(float(value) * 100)

            # Use smooth animation for progress updates
            if self._progress_animation.state() == QPropertyAnimation.State.Running:
                self._progress_animation.stop()

            current_value = self.progress_bar.value()
            # Only animate if there's a meaningful change (avoid micro-animations)
            if abs(scaled_value - current_value) > 10:  # More than 0.1% change
                self._progress_animation.setStartValue(current_value)
                self._progress_animation.setEndValue(scaled_value)
                self._progress_animation.start()
            else:
                self.progress_bar.setValue(scaled_value)
        except Exception as e:
            logger.exception(f"Progress bar update error: {e}")

    def toggle_pause(self: "SageApp") -> None:
        if self.current_download:
            self.current_download.paused = not self.current_download.paused
            if self.current_download.paused:
                self.pause_btn.setText(_("buttons.resume"))
                self.signals.update_status.emit(_("download.paused"))
            else:
                self.pause_btn.setText(_("buttons.pause"))
                self.signals.update_status.emit(_("download.resumed"))

    def cancel_download(self: "SageApp") -> None:
        if self.current_download:
            self.current_download.cancelled = True
            self.set_status_message_animated(_("status.cancelling"))  # Set status directly
            self.download_details_label.setText("")  # Clear details label on cancellation

    def toggle_download_controls(self: "SageApp", enabled=True) -> None:
        """Enable or disable download-related controls"""
        self.url_input.setEnabled(enabled)
        # Analyze button should only be enabled if there's text in the URL input
        if enabled:
            self.analyze_button.setEnabled(bool(self.url_input.text().strip()))
        else:
            self.analyze_button.setEnabled(False)
        self.format_table.setEnabled(enabled)  # Changed from format_scroll_area to format_table
        self.download_btn.setEnabled(enabled)
        if hasattr(self, "subtitle_combo"):
            self.subtitle_combo.setEnabled(enabled)  # type: ignore[reportAttributeAccessIssue]
        self.video_button.setEnabled(enabled)
        self.audio_button.setEnabled(enabled)
        self.merge_subs_checkbox.setEnabled(enabled)  # Enable/disable merge subs checkbox
        self.custom_options_btn.setEnabled(enabled)  # Enable/disable custom options button
        if hasattr(self, "llm_segment_checkbox"):
            self.llm_segment_checkbox.setEnabled(enabled)  # Enable/disable LLM segment checkbox
        self.settings_button.setEnabled(enabled)  # Enable/disable settings button

        # Clear progress/status when controls are re-enabled
        if enabled:
            self.progress_bar.setValue(0)  # Reset progress (range is 0-10000)
            self.status_label.setText(_("status.ready"))
            self.download_details_label.setText("")  # Clear details label

    def file_already_exists(self: "SageApp", filename) -> None:
        """Handle case when file already exists - simplified version"""
        self.toggle_download_controls(True)
        self.pause_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setValue(10000)  # 100% in 0-10000 range

        # Determine file type based on extension
        ext = Path(filename).suffix.lower()

        # Video file extensions
        if ext in VIDEO_EXTENSIONS:
            self.status_label.setText(_("status.video_file_exists"))
        # Audio file extensions
        elif ext in AUDIO_EXTENSIONS:
            self.status_label.setText(_("status.audio_file_exists"))
        # Subtitle file extensions
        elif ext in SUBTITLE_EXTENSIONS:
            self.status_label.setText(_("status.subtitle_file_exists"))
        # Default case
        else:
            self.status_label.setText(_("status.file_exists"))

        # Show a simple message dialog
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(_("file_exists_dialog.title"))
        msg_box.setText(_("file_exists_dialog.message", filename=filename))
        msg_box.setInformativeText(_("file_exists_dialog.info"))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Set the window icon to match the main application
        msg_box.setWindowIcon(self.windowIcon())

        # Style the dialog
        msg_box.setStyleSheet(StyleSheet.FILE_EXISTS_DIALOG)

        msg_box.exec()
