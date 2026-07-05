"""
Selection dialogs for SageDLP application.
Contains dialogs for selecting subtitles and playlist videos.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...utils.sage_localization import _
from .sage_dialogs_base import (
    ACCENT,
    ACCENT_HOVER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    BORDER,
    checkbox_qss,
    dialog_base_qss,
    secondary_button_qss,
    apply_base_stylesheet,
)


class SubtitleSelectionDialog(QDialog):
    def __init__(self, available_manual, available_auto, previously_selected, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("dialogs.select_subtitles"))
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.available_manual = available_manual
        self.available_auto = available_auto
        self.previously_selected = set(previously_selected)  # Use a set for quick lookups
        self.selected_subtitles = list(previously_selected)  # Initialize with previous selection

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Scroll Area for the list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")  # Remove border around scroll area
        layout.addWidget(scroll_area)

        # Container widget for list items (needed for scroll area)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)  # Compact spacing
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align items to top
        scroll_area.setWidget(self.list_container)

        # Populate the list initially
        self.populate_list()

        # OK and Cancel buttons
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(_("buttons.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton(_("buttons.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Style the buttons
        for button in button_box.buttons():
            button.setStyleSheet(secondary_button_qss())
            if button_box.buttonRole(button) == QDialogButtonBox.ButtonRole.AcceptRole:
                button.setStyleSheet(
                    button.styleSheet()
                    + f"QPushButton {{ background-color: {ACCENT}; border-color: {ACCENT_HOVER}; }} QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
                )

        layout.addWidget(button_box)

    def populate_list(self, filter_text="") -> None:
        # Clear existing checkboxes from layout
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Only show en and zh-hans subtitles
        target_langs = {"en", "zh-hans", "zh"}
        combined_subs = {}

        # Add manual subs
        for lang_code, sub_info in self.available_manual.items():
            if lang_code.lower() in target_langs:
                combined_subs[lang_code] = f"{lang_code} - Manual"

        # Add auto subs (only if no manual exists)
        for lang_code, sub_info in self.available_auto.items():
            if lang_code.lower() in target_langs and lang_code not in combined_subs:
                combined_subs[lang_code] = f"{lang_code} - Auto-generated"

        if not combined_subs:
            no_subs_label = QLabel(_("dialogs.no_subtitles_available"))
            no_subs_label.setStyleSheet(f"color: {TEXT_MUTED}; padding: 10px;")
            self.list_layout.addWidget(no_subs_label)
            return

        # Sort by language code
        sorted_lang_codes = sorted(combined_subs.keys())

        for lang_code in sorted_lang_codes:
            item_text = combined_subs[lang_code]
            checkbox = QCheckBox(item_text)
            checkbox.setProperty("subtitle_id", item_text)
            checkbox.setChecked(item_text in self.previously_selected)
            checkbox.stateChanged.connect(self.update_selection)
            checkbox.setStyleSheet(checkbox_qss(square=True))
            self.list_layout.addWidget(checkbox)

        self.list_layout.addStretch()

    def update_selection(self, state) -> None:
        sender = self.sender()
        subtitle_id = sender.property("subtitle_id")
        if state == Qt.CheckState.Checked.value:
            if subtitle_id not in self.previously_selected:
                self.previously_selected.add(subtitle_id)
        else:
            if subtitle_id in self.previously_selected:
                self.previously_selected.remove(subtitle_id)

    def get_selected_subtitles(self) -> list:
        # Return the final set as a list
        return list(self.previously_selected)

    def accept(self) -> None:
        # Update the final list before closing
        self.selected_subtitles = self.get_selected_subtitles()
        super().accept()


class PlaylistSelectionDialog(QDialog):
    def __init__(self, playlist_entries, previously_selected_string, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("playlist.select_videos_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)  # Allow more vertical space

        self.playlist_entries = playlist_entries
        self.checkboxes = []

        # Main layout
        main_layout = QVBoxLayout(self)

        # Filter Input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(_("dialogs.filter_playlist_placeholder"))
        self.filter_input.textChanged.connect(self.filter_list)
        self.filter_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {SURFACE_DARK};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 5px;
                min-height: 30px;
                color: {TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
        """
        )
        main_layout.addWidget(self.filter_input)

        # Top buttons (Select/Deselect All)
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton(_("buttons.select_all"))
        deselect_all_btn = QPushButton(_("buttons.deselect_all"))
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        # Style the buttons to match the subtitle dialog
        select_all_btn.setStyleSheet(secondary_button_qss())
        deselect_all_btn.setStyleSheet(select_all_btn.styleSheet())
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")  # Remove border around scroll area
        scroll_widget = QWidget()
        self.list_layout = QVBoxLayout(scroll_widget)  # Layout for checkboxes
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)  # Compact spacing
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align items to top
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Populate checkboxes
        self._populate_list(previously_selected_string)

        # Dialog buttons (OK/Cancel)
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(_("buttons.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton(_("buttons.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Style the buttons to match subtitle dialog
        for button in button_box.buttons():
            button.setStyleSheet(secondary_button_qss())
            # Style the OK button specifically if needed
            if button_box.buttonRole(button) == QDialogButtonBox.ButtonRole.AcceptRole:
                button.setStyleSheet(
                    button.styleSheet()
                    + f"QPushButton {{ background-color: {ACCENT}; border-color: {ACCENT_HOVER}; }} QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
                )

        main_layout.addWidget(button_box)

        # Apply styling to match subtitle dialog
        self.setStyleSheet(dialog_base_qss())

    def _parse_selection_string(self, selection_string) -> set:
        """Parses a yt-dlp playlist selection string (e.g., '1-3,5,7-9') into a set of 1-based indices."""
        selected_indices = set()
        if not selection_string:
            # If no previous selection, assume all are selected initially
            return set(range(1, len(self.playlist_entries) + 1))

        parts = selection_string.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                try:
                    start, end = map(int, part.split("-"))
                    if start <= end:
                        selected_indices.update(range(start, end + 1))
                except ValueError:
                    pass  # Ignore invalid ranges
            else:
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    pass  # Ignore invalid numbers
        return selected_indices

    def filter_list(self, text: str) -> None:
        """Filter the list of checkboxes based on title."""
        text = text.lower()
        for checkbox in self.checkboxes:
            title = (checkbox.property("full_title") or "").lower()
            checkbox.setVisible(text in title)

    def _populate_list(self, previously_selected_string) -> None:
        """Populates the scroll area with checkboxes for each video."""
        selected_indices = self._parse_selection_string(previously_selected_string)

        # Clear existing checkboxes if any (e.g., if repopulating)
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.checkboxes.clear()

        for index, entry in enumerate(self.playlist_entries):
            if not entry:
                continue  # Skip None entries if yt-dlp returns them

            video_index = index + 1  # yt-dlp uses 1-based indexing
            title = entry.get("title", f"Video {video_index}")

            # Format duration
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

            # Shorten title if too long but keep enough space for duration
            max_len = 65
            display_title = (title[:max_len] + "...") if len(title) > max_len + 3 else title

            checkbox = QCheckBox(f"{video_index}. {display_title}{duration_str}")
            checkbox.setChecked(video_index in selected_indices)
            checkbox.setProperty("video_index", video_index)  # Store index
            checkbox.setProperty("full_title", title) # Store full title for filtering
            checkbox.setStyleSheet(checkbox_qss(square=True))
            self.list_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)
        self.list_layout.addStretch()  # Push checkboxes to the top

    def _select_all(self) -> None:
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def _condense_indices(self, indices: list[int]) -> str:
        """Condenses a list of 1-based indices into a yt-dlp selection string."""
        if not indices:
            return ""

        # Remove duplicates and sort in one step
        indices = sorted(set(indices))

        ranges = []
        start = end = indices[0]

        for num in indices[1:]:
            if num == end + 1:
                end = num
            else:
                ranges.append(f"{start}-{end}" if start != end else str(start))
                start = end = num

        # Append the last range
        ranges.append(f"{start}-{end}" if start != end else str(start))

        return ",".join(ranges)

    def get_selected_items_string(self) -> str | None:
        """Returns the selection string based on checked boxes."""
        selected_indices = [cb.property("video_index") for cb in self.checkboxes if cb.isChecked()]

        # Check if all items are selected
        if len(selected_indices) == len(self.playlist_entries):
            return None  # yt-dlp default is all items, so return None or empty string

        return self._condense_indices(selected_indices)


