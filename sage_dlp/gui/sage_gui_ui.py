# -*- coding: utf-8 -*-
"""
Main UI construction mixin for SageDLP GUI.

`UIMixin` builds the central widget layout: URL input row, video-info and
playlist sections, format controls, format table, download buttons, and the
progress/status area. It also hosts the small UI-helper slots wired to those
widgets (URL text changes, settings tooltips, paste, mode toggles, etc.).
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Slot
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..utils.sage_flow_layout import FlowLayout
from ..utils.sage_localization import _
from .sage_stylesheet import StyleSheet
from .sage_gui_dialogs.sage_dialogs_base import empty_state_widget

if TYPE_CHECKING:
    from .sage_gui_main import SageApp


class UIMixin:
    """Constructs the main window's central widget and its UI helpers."""

    def init_ui(self: "SageApp") -> None:
        self.setWindowTitle(f"{_('app.title')}  {_('app.version', version=self.version)}")
        self.setMinimumSize(900, 750)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        # URL input section
        url_layout = QHBoxLayout()
        url_layout.setSpacing(10)

        self.url_input = QLineEdit()
        self._update_url_placeholder()
        self.url_input.returnPressed.connect(self.analyze_url)  # Analyze on Enter key
        self.url_input.textChanged.connect(self._on_url_text_changed)  # Enable/disable analyze button
        self.url_input.setMinimumHeight(42)

        # Paste URL button
        self.paste_button = QPushButton(_("buttons.paste_url"))
        self.paste_button.clicked.connect(self.paste_url)
        self.paste_button.setMinimumHeight(42)
        self.paste_button.setMinimumWidth(115)
        self.paste_button.setStyleSheet(StyleSheet.PASTE_BUTTON)

        # Analyze button with app's red theme
        self.analyze_button = QPushButton(_("buttons.analyze"))
        self.analyze_button.clicked.connect(self.analyze_url)
        self.analyze_button.setEnabled(False)  # Disabled until URL is entered
        self.analyze_button.setMinimumHeight(42)
        self.analyze_button.setMinimumWidth(115)
        self.analyze_button.setStyleSheet(StyleSheet.ANALYZE_BUTTON)

        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.paste_button)
        url_layout.addWidget(self.analyze_button)

        layout.addLayout(url_layout)

        # Video info container
        video_info_container = QWidget()
        video_info_layout = QVBoxLayout(video_info_container)
        video_info_layout.setSpacing(5)
        video_info_layout.setContentsMargins(0, 0, 0, 0)

        # Add media info layout (Thumbnail | Video Details)
        media_info_layout = self.setup_video_info_section()
        video_info_layout.addLayout(media_info_layout)

        # Add video info container to main layout
        layout.addWidget(video_info_container)

        # --- Add Playlist Info Section Directly to Main Layout ---
        # Add playlist info label (initially hidden)
        self.playlist_info_label = self.setup_playlist_info_section()
        layout.addWidget(self.playlist_info_label)

        # Playlist buttons layout
        playlist_btns_layout = QHBoxLayout()

        # Add playlist selection BUTTON (initially hidden) - REPLACED QLineEdit
        self.playlist_select_btn = QPushButton(_("buttons.select_videos"))
        self.playlist_select_btn.clicked.connect(self.open_playlist_selection_dialog)
        self.playlist_select_btn.setVisible(False)
        self.playlist_select_btn.setStyleSheet(StyleSheet.PLAYLIST_BUTTON)
        playlist_btns_layout.addWidget(self.playlist_select_btn)

        # Save playlist as button
        self.save_playlist_btn = QPushButton(_("buttons.save_playlist"))
        self.save_playlist_btn.clicked.connect(self.save_playlist_to_file)
        self.save_playlist_btn.setVisible(False)
        self.save_playlist_btn.setStyleSheet(StyleSheet.PLAYLIST_BUTTON)
        playlist_btns_layout.addWidget(self.save_playlist_btn)

        layout.addLayout(playlist_btns_layout)
        # --- End Playlist Info Section ---

        # Format controls section with minimal spacing
        layout.addSpacing(5)

        # Format selection layout (wrapping flow layout for narrow windows)
        self.format_layout = FlowLayout(spacing=8)

        # Show formats label
        self.show_formats_label = QLabel(_("formats.show_formats"))
        self.show_formats_label.setStyleSheet("color: #0f172a;")
        self.format_layout.addWidget(self.show_formats_label)

        # Format buttons group
        self.format_buttons = QButtonGroup(self)
        self.format_buttons.setExclusive(True)

        # Video button
        self.video_button = QPushButton(_("buttons.video"))
        self.video_button.setCheckable(True)
        self.video_button.setChecked(True)  # Set video as default
        self.video_button.setStyleSheet(StyleSheet.FORMAT_TOGGLE_BUTTON)
        self.format_buttons.addButton(self.video_button)
        self.format_layout.addWidget(self.video_button)

        # Audio button
        self.audio_button = QPushButton(_("buttons.audio_only"))
        self.audio_button.setCheckable(True)
        self.audio_button.setStyleSheet(StyleSheet.FORMAT_TOGGLE_BUTTON)
        self.format_buttons.addButton(self.audio_button)
        self.format_layout.addWidget(self.audio_button)

        # Subtitle-only button (download only word-level timestamped subtitles + run segmentation)
        self.subtitle_only_button = QPushButton(_("buttons.subtitle_only"))
        self.subtitle_only_button.setCheckable(True)
        self.subtitle_only_button.setStyleSheet(StyleSheet.FORMAT_TOGGLE_BUTTON)
        self.subtitle_only_button.setToolTip(_("main_ui.subtitle_only_tooltip"))
        self.format_buttons.addButton(self.subtitle_only_button)
        self.format_layout.addWidget(self.subtitle_only_button)

        # Add Merge Subtitles checkbox (Moved here)
        self.merge_subs_checkbox = QCheckBox(_("main_ui.merge_subtitles"))
        self.merge_subs_checkbox.setStyleSheet(StyleSheet.CHECKBOX)
        # Initially disable it, will be enabled if subtitles are selected later
        self.merge_subs_checkbox.setEnabled(False)
        self.format_layout.addWidget(self.merge_subs_checkbox)

        # Add Save Thumbnail Checkbox (Moved here)
        self.save_thumbnail_checkbox = QCheckBox(_("main_ui.save_thumbnail"))
        self.save_thumbnail_checkbox.setChecked(False)
        self.save_thumbnail_checkbox.stateChanged.connect(self.toggle_save_thumbnail)
        self.save_thumbnail_checkbox.setStyleSheet(StyleSheet.CHECKBOX)
        self.format_layout.addWidget(self.save_thumbnail_checkbox)

        # Add Save Description Checkbox (Moved here)
        self.save_description_checkbox = QCheckBox(_("main_ui.save_description"))
        self.save_description_checkbox.setChecked(False)
        self.save_description_checkbox.stateChanged.connect(self.toggle_save_description)
        self.save_description_checkbox.setStyleSheet(StyleSheet.CHECKBOX)
        self.format_layout.addWidget(self.save_description_checkbox)

        # Add Embed Chapters Checkbox
        self.embed_chapters_checkbox = QCheckBox(_("main_ui.embed_chapters"))
        self.embed_chapters_checkbox.setChecked(False)
        self.embed_chapters_checkbox.stateChanged.connect(self.toggle_embed_chapters)
        self.embed_chapters_checkbox.setStyleSheet(StyleSheet.CHECKBOX)
        self.format_layout.addWidget(self.embed_chapters_checkbox)

        # Add LLM Segment Checkbox
        self.llm_segment_checkbox = QCheckBox("LLM Segment")
        self.llm_segment_checkbox.setChecked(False)
        self.llm_segment_checkbox.setEnabled(False)  # enabled only when subtitles selected
        self.llm_segment_checkbox.setStyleSheet(StyleSheet.CHECKBOX)
        self.llm_segment_checkbox.setToolTip(_("llm.checkbox_tooltip"))
        self.format_layout.addWidget(self.llm_segment_checkbox)

        layout.addLayout(self.format_layout)

        # Format table with stacked empty state
        self.format_table_stack = QStackedWidget()
        self._empty_state = empty_state_widget(
            _("formats.no_formats_title"),
            _("formats.no_formats_desc"),
        )
        self.format_table_stack.addWidget(self._empty_state)  # index 0 = empty state
        format_table = self.setup_format_table()
        self.format_table_stack.addWidget(format_table)       # index 1 = actual table
        self.format_table_stack.setCurrentIndex(0)            # start with empty state
        layout.addWidget(self.format_table_stack, stretch=1)

        # Download section
        download_layout = QHBoxLayout()

        # Replace the two separate buttons with a single Custom Options button
        self.custom_options_btn = QPushButton(_("buttons.custom_options"))
        self.custom_options_btn.clicked.connect(self.show_custom_options)
        self.custom_options_btn.setStyleSheet(StyleSheet.SECONDARY_BUTTON)


        # --- Rename Path Button to Settings Button ---
        self.settings_button = QPushButton(_("buttons.download_settings"))  # Renamed button
        self.settings_button.clicked.connect(self.show_download_settings_dialog)  # Renamed method
        self._update_settings_tooltip()
        self.settings_button.setStyleSheet(StyleSheet.SECONDARY_BUTTON)
        # --- End Settings Button ---

        self.download_btn = QPushButton(_("buttons.download"))
        self.download_btn.clicked.connect(self.start_download)

        # Add pause and cancel buttons
        self.pause_btn = QPushButton(_("buttons.pause"))
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setVisible(False)  # Hidden initially
        self.pause_btn.setStyleSheet(StyleSheet.WARNING_BUTTON)

        self.cancel_btn = QPushButton(_("buttons.cancel"))
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setVisible(False)  # Hidden initially
        self.cancel_btn.setStyleSheet(StyleSheet.DANGER_BUTTON)

        # Add all buttons to layout in the correct order
        download_layout.addWidget(self.custom_options_btn)
        download_layout.addWidget(self.settings_button)
        download_layout.addWidget(self.download_btn)
        download_layout.addWidget(self.pause_btn)
        download_layout.addWidget(self.cancel_btn)

        layout.addLayout(download_layout)

        # Progress section with improved styling
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10000)  # Use 0-10000 range for 0.01% precision
        self.progress_bar.setFormat("%p%")  # Display as percentage
        self.progress_bar.setStyleSheet(StyleSheet.PROGRESS_BAR)
        progress_layout.addWidget(self.progress_bar)

        # Setup smooth animation for progress bar
        self._progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self._progress_animation.setDuration(150)  # 150ms smooth transition
        self._progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Add download details label with improved styling
        self.download_details_label = QLabel()
        self.download_details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_details_label.setStyleSheet(StyleSheet.STATUS_LABEL)
        progress_layout.addWidget(self.download_details_label)

        # Create a horizontal layout for status label and open folder button
        status_layout = QHBoxLayout()

        self.status_label = QLabel(_("app.ready"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(StyleSheet.STATUS_LABEL)
        status_layout.addWidget(self.status_label)

        # Add "Open Folder" button (initially hidden)
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.open_folder_btn.setToolTip(_("buttons.open_folder"))
        self.open_folder_btn.setFixedSize(30, 30)
        self.open_folder_btn.setStyleSheet(StyleSheet.OPEN_FOLDER_BUTTON)
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        self.open_folder_btn.setVisible(False)  # Hidden by default
        status_layout.addWidget(self.open_folder_btn)

        progress_layout.addLayout(status_layout)

        layout.addLayout(progress_layout)

        # Connect signals
        self.signals.update_formats.connect(self.update_format_table)
        self.signals.update_status.connect(self.set_status_message_animated)
        self.signals.update_progress.connect(self.update_progress_bar)

        # Connect new signals
        self.signals.playlist_info_label_visible.connect(lambda v: self.set_widget_visible_animated(self.playlist_info_label, v))
        self.signals.playlist_info_label_text.connect(self.playlist_info_label.setText)
        self.signals.selected_subs_label_text.connect(self.selected_subs_label.setText)
        self.signals.playlist_select_btn_visible.connect(lambda v: self.set_widget_visible_animated(self.playlist_select_btn, v))
        self.signals.playlist_select_btn_visible.connect(lambda v: self.set_widget_visible_animated(self.save_playlist_btn, v))
        self.signals.playlist_select_btn_text.connect(self.playlist_select_btn.setText)

        # Disable analysis-dependent controls until video is analyzed
        self.toggle_analysis_dependent_controls(enabled=False)

    # ---- Small UI helpers --------------------------------------------

    def _on_url_text_changed(self: "SageApp", text: str) -> None:
        """Enable or disable the Analyze button based on URL input content."""
        self.analyze_button.setEnabled(bool(text.strip()))

    def _get_speed_limit_tooltip_text(self: "SageApp") -> str:
        """Return the current speed limit string for the settings tooltip."""
        if self.speed_limit_value:
            return f"{self.speed_limit_value} {['KB/s', 'MB/s'][self.speed_limit_unit_index]}"
        return _("main_ui.speed_limit_none")

    def _update_settings_tooltip(self: "SageApp") -> None:
        """Refresh the download settings tooltip text."""
        self.settings_button.setToolTip(
            _(
                "main_ui.settings_tooltip",
                path=self.last_path,
                speed_limit=self._get_speed_limit_tooltip_text(),
            )
        )

    def _update_url_placeholder(self: "SageApp") -> None:
        """Update the URL placeholder based on the selected validation mode."""
        placeholder_key = "main_ui.url_placeholder_generic" if self.generic_mode_enabled else "main_ui.url_placeholder"
        self.url_input.setPlaceholderText(_(placeholder_key))

    def paste_url(self: "SageApp") -> None:
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    # --- Toggle methods ---

    def toggle_save_thumbnail(self: "SageApp", state) -> None:
        self.save_thumbnail = bool(state == 2)

    def toggle_save_description(self: "SageApp", state) -> None:
        self.save_description = bool(state == 2)

    def toggle_embed_chapters(self: "SageApp", state) -> None:
        self.embed_chapters = bool(state == 2)

    def handle_mode_change(self: "SageApp") -> None:
        """Enable or disable features based on video/audio/subtitle-only mode"""
        # Only allow enabling if analysis is complete
        can_enable = self.analysis_completed
        is_audio = self.audio_button.isChecked()
        is_subtitle_only = hasattr(self, "subtitle_only_button") and self.subtitle_only_button.isChecked()

        if is_subtitle_only:
            # Subtitle-only mode: disable video/audio-specific features
            self.merge_subs_checkbox.setEnabled(False)
            self.merge_subs_checkbox.setChecked(False)
            self.merge_subs_checkbox.setToolTip(_("main_ui.subtitle_only_mode"))

            # Save thumbnail / description / chapters 不适用于仅字幕模式
            for attr, tip in [
                ("save_thumbnail_checkbox", _("main_ui.subtitle_only_mode")),
                ("save_description_checkbox", _("main_ui.subtitle_only_mode")),
                ("embed_chapters_checkbox", _("main_ui.subtitle_only_mode")),
            ]:
                cb = getattr(self, attr, None)
                if cb is not None:
                    cb.setEnabled(False)
                    cb.setChecked(False)
                    cb.setToolTip(tip)

            # LLM 智能断句在仅字幕模式下强制启用 LLM 模式且不可关闭
            if hasattr(self, "llm_segment_checkbox"):
                self.llm_segment_checkbox.setEnabled(False)
                self.llm_segment_checkbox.setChecked(True)
                self.llm_segment_checkbox.setToolTip(_("main_ui.subtitle_only_llm_auto_enabled"))

            # 字幕选择按钮可用（取决于是否分析完成）
            if hasattr(self, "subtitle_select_btn"):
                self.subtitle_select_btn.setEnabled(can_enable)
                if not can_enable:
                    self.subtitle_select_btn.setToolTip(_("main_ui.analyze_first_tooltip"))
                else:
                    self.subtitle_select_btn.setToolTip(_("main_ui.subtitle_only_require_subs"))
            return

        if is_audio:
            # In Audio Only mode, disable video-specific features
            self.merge_subs_checkbox.setEnabled(False)
            self.merge_subs_checkbox.setChecked(False)  # Uncheck when disabled
            if not can_enable:
                self.merge_subs_checkbox.setToolTip(_("main_ui.analyze_first_tooltip"))
            else:
                self.merge_subs_checkbox.setToolTip(_("main_ui.audio_mode_disabled"))

            # Allow subtitle selection in Audio Only mode if analysis is complete
            if hasattr(self, "subtitle_select_btn"):
                self.subtitle_select_btn.setEnabled(can_enable)
                if not can_enable:
                    self.subtitle_select_btn.setToolTip(_("main_ui.analyze_first_tooltip"))
                else:
                    self.subtitle_select_btn.setToolTip("")
        else:
            # In Video mode, enable video-specific features (if analysis complete)

            # Enable merge_subs only if subtitles are selected and analysis is complete
            has_subs_selected = len(getattr(self, "selected_subtitles", [])) > 0
            should_enable_merge = can_enable and has_subs_selected
            self.merge_subs_checkbox.setEnabled(should_enable_merge)
            if not can_enable:
                self.merge_subs_checkbox.setToolTip(_("main_ui.analyze_first_tooltip"))
            elif not has_subs_selected:
                self.merge_subs_checkbox.setToolTip(_("main_ui.select_subtitles_first"))
            else:
                self.merge_subs_checkbox.setToolTip("")

            # Enable LLM segment only if subtitles are selected and analysis is complete
            if hasattr(self, "llm_segment_checkbox"):
                self.llm_segment_checkbox.setEnabled(should_enable_merge)
                if not can_enable:
                    self.llm_segment_checkbox.setToolTip(_("main_ui.analyze_first_tooltip"))
                elif not has_subs_selected:
                    self.llm_segment_checkbox.setToolTip("")
                else:
                    self.llm_segment_checkbox.setToolTip(_("llm.checkbox_tooltip"))

            # Re-enable subtitle selection button in Video mode (if analysis complete)
            if hasattr(self, "subtitle_select_btn"):
                self.subtitle_select_btn.setEnabled(can_enable)
                if not can_enable:
                    self.subtitle_select_btn.setToolTip(_("main_ui.analyze_first_tooltip"))
                else:
                    self.subtitle_select_btn.setToolTip("")

    @Slot(bool)
    def toggle_analysis_dependent_controls(self: "SageApp", enabled=True) -> None:
        """Enable or disable controls that require video analysis to be completed"""
        # Determine tooltip text for disabled state
        tooltip_text = "" if enabled else _("main_ui.analyze_first_tooltip")

        # Subtitle selection
        if hasattr(self, "subtitle_select_btn"):
            self.subtitle_select_btn.setEnabled(enabled)
            if not enabled:
                self.subtitle_select_btn.setToolTip(tooltip_text)
            else:
                self.subtitle_select_btn.setToolTip("")

        # Save Thumbnail checkbox
        if hasattr(self, "save_thumbnail_checkbox"):
            self.save_thumbnail_checkbox.setEnabled(enabled)
            if not enabled:
                self.save_thumbnail_checkbox.setToolTip(tooltip_text)
            else:
                self.save_thumbnail_checkbox.setToolTip("")

        # Save Description checkbox
        if hasattr(self, "save_description_checkbox"):
            self.save_description_checkbox.setEnabled(enabled)
            if not enabled:
                self.save_description_checkbox.setToolTip(tooltip_text)
            else:
                self.save_description_checkbox.setToolTip("")

        # Embed Chapters checkbox
        if hasattr(self, "embed_chapters_checkbox"):
            self.embed_chapters_checkbox.setEnabled(enabled)
            if not enabled:
                self.embed_chapters_checkbox.setToolTip(tooltip_text)
            else:
                self.embed_chapters_checkbox.setToolTip("")

        # Merge Subtitles (only if subtitles are selected and not in audio / subtitle-only mode)
        if hasattr(self, "merge_subs_checkbox"):
            has_subs = len(getattr(self, "selected_subtitles", [])) > 0
            is_audio_mode = self.audio_button.isChecked()
            is_subtitle_only = hasattr(self, "subtitle_only_button") and self.subtitle_only_button.isChecked()
            should_enable = enabled and has_subs and not is_audio_mode and not is_subtitle_only
            self.merge_subs_checkbox.setEnabled(should_enable)
            if not enabled:
                self.merge_subs_checkbox.setToolTip(tooltip_text)
            elif not has_subs:
                self.merge_subs_checkbox.setToolTip(_("main_ui.select_subtitles_first"))
            elif is_audio_mode:
                self.merge_subs_checkbox.setToolTip(_("main_ui.audio_mode_disabled"))
            elif is_subtitle_only:
                self.merge_subs_checkbox.setToolTip(_("main_ui.subtitle_only_mode"))
            else:
                self.merge_subs_checkbox.setToolTip("")

        # Subtitle-only 模式下，重新应用其专属 UI 状态（强制 LLM 勾选等）
        if hasattr(self, "subtitle_only_button") and self.subtitle_only_button.isChecked():
            self.handle_mode_change()
