"""
Base dialogs for SageDLP application.
Contains basic utility dialogs like LogWindow and AboutDialog,
as well as shared QSS constants for all dialog files.
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
from ...utils.sage_localization import _
from ...utils.sage_logger import logger
from ...utils.sage_constants import APP_LOG_DIR

from ...core.sage_ffmpeg import get_ffmpeg_path
from ...core.sage_utils import _version_cache, check_ffmpeg, get_ffmpeg_version, get_ytdlp_version, refresh_version_cache
from ...core.sage_yt_dlp import check_ytdlp_installed, get_yt_dlp_path


# ═══════════════════════════════════════════════════════
# Shared design tokens (imported by all dialog files)
# ═══════════════════════════════════════════════════════
ACCENT = "#2a4a82"
ACCENT_HOVER = "#1e3660"
ACCENT_PRESSED = "#162d4f"
SURFACE = "#f8fafc"
SURFACE_DARK = "#f1f5f9"
WHITE = "#ffffff"
BORDER = "#cbd5e1"
BORDER_FOCUS = "#2a4a82"
TEXT_PRIMARY = "#0f172a"
TEXT_SECONDARY = "#64748b"
TEXT_MUTED = "#94a3b8"
BG_INPUT = "#ffffff"
SUCCESS = "#059669"
WARNING = "#ffaa00"
ERROR = "#ff6666"


# ═══════════════════════════════════════════════════════
# Shared QSS helpers (f-string ready for token values)
# ═══════════════════════════════════════════════════════

def dialog_base_qss() -> str:
    return f"""
        QDialog {{ background-color: {SURFACE}; }}
        QLabel {{ color: {TEXT_PRIMARY}; }}
        QWidget {{ background-color: {SURFACE}; }}
    """


def primary_button_qss(*, min_width: str = "100px") -> str:
    return f"""
        QPushButton {{
            padding: 8px 15px;
            background-color: {ACCENT};
            border: none;
            border-radius: 6px;
            color: white;
            font-weight: bold;
            min-width: {min_width};
        }}
        QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}
        QPushButton:disabled {{ background-color: {BORDER}; color: {TEXT_SECONDARY}; }}
    """


def secondary_button_qss() -> str:
    return f"""
        QPushButton {{
            background-color: {SURFACE_DARK};
            border: 2px solid {BORDER};
            border-radius: 6px;
            padding: 5px 15px;
            min-height: 30px;
            color: {TEXT_PRIMARY};
        }}
        QPushButton:hover {{ background-color: #475569; color: white; }}
        QPushButton:pressed {{ background-color: #64748b; color: white; }}
    """


def lineedit_qss() -> str:
    return f"""
        QLineEdit {{
            padding: 8px;
            border: 2px solid {BORDER};
            border-radius: 6px;
            background-color: {WHITE};
            color: {TEXT_PRIMARY};
            selection-background-color: {ACCENT};
            selection-color: white;
        }}
        QLineEdit:focus {{ border-color: {ACCENT}; }}
    """


def checkbox_qss(*, square: bool = False) -> str:
    radius = "4px" if square else "9px"
    return f"""
        QCheckBox {{
            color: {TEXT_PRIMARY};
            spacing: 5px;
            padding: 3px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {radius};
        }}
        QCheckBox::indicator:unchecked {{
            border: 2px solid {BORDER};
            background: {WHITE};
        }}
        QCheckBox::indicator:checked {{
            border: 2px solid {ACCENT};
            background: {ACCENT};
        }}
        QCheckBox:disabled {{ color: {TEXT_MUTED}; }}
        QCheckBox::indicator:disabled {{ border-color: {BORDER}; background: {SURFACE_DARK}; }}
    """


def radio_button_qss() -> str:
    return f"""
        QRadioButton {{
            color: {TEXT_PRIMARY};
            spacing: 5px;
            padding: 5px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
        }}
        QRadioButton::indicator:unchecked {{
            border: 2px solid {BORDER};
            background: {WHITE};
        }}
        QRadioButton::indicator:checked {{
            border: 2px solid {ACCENT};
            background: {ACCENT};
        }}
    """


def groupbox_qss() -> str:
    return f"""
        QGroupBox {{
            border: 1px solid {BORDER};
            border-radius: 6px;
            margin-top: 1.5ex;
            color: {TEXT_PRIMARY};
            padding: 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {TEXT_PRIMARY};
        }}
    """


def combobox_qss() -> str:
    return f"""
        QComboBox {{
            padding: 8px;
            border: 2px solid {BORDER};
            border-radius: 6px;
            background-color: {WHITE};
            color: {TEXT_PRIMARY};
            min-width: 150px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            border: none;
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {WHITE};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT};
            selection-color: white;
        }}
    """


def tab_widget_qss() -> str:
    return f"""
        QFrame#tabContent {{
            border: 1px solid {BORDER};
            background-color: {SURFACE};
        }}
        QTabBar::tab {{
            background-color: {WHITE};
            color: {TEXT_SECONDARY};
            padding: 8px 12px;
            border: 1px solid {BORDER};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {ACCENT};
            color: white;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: #eff4fa;
        }}
    """


def help_label_qss() -> str:
    return f"""
        QLabel {{
            color: {TEXT_SECONDARY};
            font-size: 11px;
        }}
    """


def progress_bar_qss() -> str:
    return f"""
        QProgressBar {{
            border: 2px solid {BORDER};
            border-radius: 8px;
            text-align: center;
            color: {TEXT_PRIMARY};
            background-color: {WHITE};
            height: 24px;
        }}
        QProgressBar::chunk {{
            background-color: {ACCENT};
            border-radius: 6px;
        }}
    """


def message_box_qss() -> str:
    return f"""
        QMessageBox {{
            background-color: {SURFACE};
            color: {TEXT_PRIMARY};
        }}
        QMessageBox QLabel {{
            color: {TEXT_PRIMARY};
        }}
        QMessageBox QPushButton {{
            padding: 8px 15px;
            background-color: {ACCENT};
            border: none;
            border-radius: 6px;
            color: white;
            font-weight: bold;
            min-width: 80px;
        }}
        QMessageBox QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        QMessageBox QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}
    """


def apply_base_stylesheet(dialog: QDialog) -> None:
    """Apply the shared dialog background + QLabel colors to any dialog."""
    dialog.setStyleSheet(dialog_base_qss())


# ═══════════════════════════════════════════════════════
# Empty state / placeholder helpers
# ═══════════════════════════════════════════════════════

EMPTY_STATE_STYLE = f"""
    QWidget#emptyStateContainer {{
        background-color: {WHITE};
        border: 2px dashed {BORDER};
        border-radius: 12px;
    }}
    QLabel#emptyStateIcon {{
        font-size: 32px;
        color: {TEXT_MUTED};
    }}
    QLabel#emptyStateTitle {{
        font-size: 14px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}
    QLabel#emptyStateDesc {{
        font-size: 12px;
        color: {TEXT_SECONDARY};
    }}
"""


def empty_state_widget(title: str, description: str, icon_text: str = "▷") -> QWidget:
    """Create an empty state placeholder widget with icon, title, and description."""
    widget = QWidget()
    widget.setObjectName("emptyStateContainer")
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(8)

    icon_label = QLabel(icon_text)
    icon_label.setObjectName("emptyStateIcon")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    title_label = QLabel(title)
    title_label.setObjectName("emptyStateTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    desc_label = QLabel(description)
    desc_label.setObjectName("emptyStateDesc")
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_label.setWordWrap(True)

    layout.addStretch(2)
    layout.addWidget(icon_label)
    layout.addWidget(title_label)
    layout.addWidget(desc_label)
    layout.addStretch(3)

    widget.setStyleSheet(EMPTY_STATE_STYLE)
    return widget


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
                background-color: #f1f5f9;
                color: #0f172a;
                font-family: Consolas, monospace;
                font-size: 12px;
                border: 2px solid #cbd5e1;
                border-radius: 8px;
            }
        """
        )

        layout.addWidget(self.log_text)

    def append_log(self, message) -> None:
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
