"""
Zenith Editorial Design System Stylesheet for SageDLP.
Modern SaaS utility meets Cinematic elegance.

Design Tokens:
  Accent: #2a4a82 | Success: #059669 | Surface: #f8fafc
  8px spacing grid | Rounded corners | Diffuse shadows
  Typography: -apple-system, Segoe UI, system-ui, sans-serif
"""


class StyleSheet:
    # ═══════════════════════════════════════════════════════════
    # Design Tokens
    # ═══════════════════════════════════════════════════════════
    ACCENT = "#2a4a82"
    ACCENT_HOVER = "#1e3660"
    ACCENT_PRESSED = "#162d4f"
    SUCCESS = "#059669"
    SUCCESS_HOVER = "#047857"
    SUCCESS_PRESSED = "#065f46"
    SURFACE = "#f8fafc"
    SURFACE_DARK = "#f1f5f9"
    WHITE = "#ffffff"
    BORDER = "#cbd5e1"
    BORDER_DARK = "#94a3b8"
    GRIDLINE = "#e2e8f0"
    TEXT_PRIMARY = "#0f172a"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED = "#94a3b8"
    TEXT_PLACEHOLDER = "#64748b"
    BG_HOVER = "#eff4fa"

    # ═══════════════════════════════════════════════════════════
    # Border-radius hierarchy
    # ═══════════════════════════════════════════════════════════
    RADIUS_CONTAINER = "12px"  # QDialog, QMainWindow
    RADIUS_CARD = "8px"        # QGroupBox, QTableWidget, cards
    RADIUS_CONTROL = "6px"     # QPushButton, QLineEdit, QComboBox

    # ═══════════════════════════════════════════════════════════
    # Typography
    # ═══════════════════════════════════════════════════════════
    FONT_FAMILY = "-apple-system, 'Segoe UI', system-ui, sans-serif"
    FONT_MONO = "'Consolas', 'Courier New', monospace"

    # ═══════════════════════════════════════════════════════════
    # QSS strings — built lazily on first access via descriptors
    # ═══════════════════════════════════════════════════════════

    _MAIN: str | None = None
    _PASTE_BUTTON: str | None = None
    _ANALYZE_BUTTON: str | None = None
    _PLAYLIST_BUTTON: str | None = None
    _FORMAT_TOGGLE_BUTTON: str | None = None
    _CHECKBOX: str | None = None
    _PROGRESS_BAR: str | None = None
    _STATUS_LABEL: str | None = None
    _OPEN_FOLDER_BUTTON: str | None = None
    _SECONDARY_BUTTON: str | None = None
    _WARNING_BUTTON: str | None = None
    _DANGER_BUTTON: str | None = None
    _UPDATE_DIALOG_MESSAGE: str | None = None
    _UPDATE_DIALOG_CHANGELOG: str | None = None
    _UPDATE_DIALOG_DOWNLOAD_BTN: str | None = None
    _UPDATE_DIALOG_REMIND_BTN: str | None = None
    _UPDATE_DIALOG_MAIN: str | None = None
    _FILE_EXISTS_DIALOG: str | None = None
    _SETUP_SUCCESS_DIALOG: str | None = None

    @classmethod
    def _build_all(cls) -> None:
        a = cls.ACCENT
        ah = cls.ACCENT_HOVER
        ap = cls.ACCENT_PRESSED
        s = cls.SURFACE
        sd = cls.SURFACE_DARK
        w = cls.WHITE
        b = cls.BORDER
        bd = cls.BORDER_DARK
        g = cls.GRIDLINE
        tp = cls.TEXT_PRIMARY
        ts = cls.TEXT_SECONDARY
        tm = cls.TEXT_MUTED
        tpl = cls.TEXT_PLACEHOLDER
        ff = cls.FONT_FAMILY
        rcon = cls.RADIUS_CONTAINER  # container: 12px
        rcard = cls.RADIUS_CARD      # card: 8px
        rctrl = cls.RADIUS_CONTROL   # control: 6px

        cls._MAIN = f"""
            QMainWindow {{
                background-color: {s};
            }}
            QWidget {{
                background-color: {s};
                color: {tp};
                font-family: {ff};
            }}
            QLineEdit {{
                padding: 8px 16px;
                border: 2px solid {b};
                border-radius: {rctrl};
                background-color: {w};
                color: {tp};
                font-size: 13px;
                selection-background-color: {sd};
                selection-color: {a};
            }}
            QLineEdit:focus {{
                border-color: {a};
                border-width: 2px;
            }}
            QLineEdit:disabled {{
                background-color: {sd};
                color: {tm};
            }}
            QPushButton {{
                padding: 8px 16px;
                background-color: {a};
                border: 2px solid transparent;
                border-radius: {rctrl};
                color: white;
                font-weight: 600;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {ah};
            }}
            QPushButton:pressed {{
                background-color: {ap};
            }}
            QPushButton:focus {{
                border-color: {a};
                outline: none;
            }}
            QPushButton:disabled {{
                background-color: {b};
                color: {tm};
            }}
            QTableWidget {{
                border: 2px solid {b};
                border-radius: {rcard};
                background-color: {w};
                gridline-color: {g};
                font-family: {ff};
            }}
            QHeaderView::section {{
                background-color: {sd};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {a};
                color: {tp};
                font-weight: 600;
            }}
            QProgressBar {{
                border: 2px solid {b};
                border-radius: 8px;
                text-align: center;
                color: {tp};
                background-color: {w};
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {a};
                border-radius: 6px;
            }}
            QLabel {{
                color: {tp};
                font-family: {ff};
            }}
            QPushButton.filter-btn {{
                background-color: {w};
                padding: 6px 12px;
                margin: 0 4px;
                border: 1px solid {b};
                color: {tp};
                border-radius: {rctrl};
                font-weight: 400;
            }}
            QPushButton.filter-btn:checked {{
                background-color: {a};
                color: white;
                border-color: {a};
            }}
            QPushButton.filter-btn:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {a};
            }}
            QPushButton.filter-btn:checked:hover {{
                background-color: {ah};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {s};
                width: 14px;
                margin: 15px 0 15px 0;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background: {b};
                min-height: 30px;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {tm};
            }}
            QScrollBar::sub-line:vertical {{
                border: none;
                background: {s};
                height: 15px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }}
            QScrollBar::add-line:vertical {{
                border: none;
                background: {s};
                height: 15px;
                border-bottom-left-radius: 7px;
                border-bottom-right-radius: 7px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:vertical:hover,
            QScrollBar::add-line:vertical:hover {{
                background: {b};
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """

        cls._PASTE_BUTTON = f"""
            QPushButton {{
                padding: 9px 20px;
                background-color: {w};
                border: 2px solid {b};
                border-radius: {rctrl};
                color: {tp};
                font-weight: 600;
                font-size: 13px;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {a};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_HOVER};
                padding: 11px 18px 7px 22px;
            }}
        """

        cls._ANALYZE_BUTTON = f"""
            QPushButton {{
                padding: 9px 20px;
                background-color: {a};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 13px;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {ah};
            }}
            QPushButton:pressed {{
                background-color: {ap};
                padding: 11px 18px 7px 22px;
            }}
            QPushButton:disabled {{
                background-color: {b};
                color: {tm};
            }}
        """

        cls._PLAYLIST_BUTTON = f"""
            QPushButton {{
                padding: 6px 12px;
                background-color: {w};
                border: 1px solid {a};
                border-radius: 8px;
                color: {a};
                font-weight: 500;
                text-align: left;
                padding-left: 10px;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {ah};
            }}
        """

        cls._FORMAT_TOGGLE_BUTTON = f"""
            QPushButton {{
                padding: 8px 16px;
                background-color: {w};
                border: 1px solid {b};
                border-radius: {rctrl};
                color: {tp};
                font-weight: 600;
                font-family: {ff};
            }}
            QPushButton:checked {{
                background-color: {a};
                color: white;
                border-color: {a};
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {a};
            }}
            QPushButton:checked:hover {{
                background-color: {ah};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_HOVER};
                padding: 10px 14px 6px 18px;
            }}
            QPushButton:checked:pressed {{
                background-color: {ap};
                padding: 10px 14px 6px 18px;
            }}
        """

        cls._CHECKBOX = f"""
            QCheckBox {{
                color: {tp};
                padding: 4px;
                margin-left: 20px;
                font-family: {ff};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid {b};
                background: {w};
                border-radius: 9px;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {a};
                background: {a};
                border-radius: 9px;
            }}
            QCheckBox:disabled {{ color: {tm}; }}
            QCheckBox::indicator:disabled {{ border-color: {g}; background: {sd}; }}
        """

        cls._PROGRESS_BAR = f"""
            QProgressBar {{
                border: 2px solid {b};
                border-radius: {rcard};
                text-align: center;
                color: {tp};
                background-color: {w};
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: {a};
                border-radius: {rctrl};
            }}
        """

        cls._STATUS_LABEL = f"""
            QLabel {{
                color: {ts};
                font-size: 12px;
                padding: 4px;
            }}
        """

        cls._OPEN_FOLDER_BUTTON = f"""
            QPushButton {{
                background-color: {w};
                color: {ts};
                border: 1px solid {b};
                border-radius: 8px;
                font-size: 16px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border: 1px solid {a};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_HOVER};
                padding: 4px 0px 0px 4px;
            }}
        """

        cls._SECONDARY_BUTTON = f"""
            QPushButton {{
                padding: 8px 16px;
                background-color: {w};
                border: 2px solid {b};
                border-radius: {rctrl};
                color: {tp};
                font-weight: 500;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {cls.BG_HOVER};
                border-color: {a};
            }}
            QPushButton:pressed {{
                background-color: {sd};
            }}
            QPushButton:disabled {{
                background-color: {sd};
                color: {tm};
                border-color: {g};
            }}
        """

        cls._WARNING_BUTTON = f"""
            QPushButton {{
                padding: 8px 16px;
                background-color: {w};
                border: 2px solid #ffaa00;
                border-radius: 8px;
                color: #b8860b;
                font-weight: 500;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: #fff8e1;
                border-color: #ff8c00;
            }}
            QPushButton:disabled {{
                background-color: {sd};
                color: {tm};
                border-color: {g};
            }}
        """

        cls._DANGER_BUTTON = f"""
            QPushButton {{
                padding: 8px 16px;
                background-color: {w};
                border: 2px solid #ef4444;
                border-radius: 8px;
                color: #dc2626;
                font-weight: 500;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: #fef2f2;
                border-color: #dc2626;
            }}
            QPushButton:disabled {{
                background-color: {sd};
                color: {tm};
                border-color: {g};
            }}
        """

        cls._UPDATE_DIALOG_MESSAGE = f"""
            QLabel {{
                background-color: {w};
                border: 1px solid {b};
                border-radius: 8px;
                padding: 16px;
                margin: 4px 0;
                color: {tp};
            }}
        """

        cls._UPDATE_DIALOG_CHANGELOG = f"""
            QTextEdit {{
                background-color: {w};
                border: 2px solid {b};
                border-radius: {rctrl};
                color: {tp};
                padding: 12px;
                font-family: {ff};
                font-size: 12px;
                line-height: 1.4;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {s};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {b};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {tm};
            }}
        """

        cls._UPDATE_DIALOG_DOWNLOAD_BTN = f"""
            QPushButton {{
                padding: 10px 20px;
                background-color: {a};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 13px;
                min-width: 140px;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {ah};
            }}
            QPushButton:pressed {{
                background-color: {ap};
            }}
        """

        cls._UPDATE_DIALOG_REMIND_BTN = f"""
            QPushButton {{
                padding: 10px 20px;
                background-color: {w};
                border: 1px solid {bd};
                border-radius: {rctrl};
                color: {tp};
                font-weight: 600;
                font-size: 13px;
                min-width: 140px;
                font-family: {ff};
            }}
            QPushButton:hover {{
                background-color: {s};
                border-color: {tpl};
            }}
            QPushButton:pressed {{
                background-color: {g};
            }}
        """

        cls._UPDATE_DIALOG_MAIN = f"""
            QDialog {{
                background-color: {s};
                border: 1px solid {b};
                border-radius: {rcon};
            }}
            QLabel {{
                color: {tp};
                font-size: 12px;
            }}
        """

        cls._FILE_EXISTS_DIALOG = f"""
            QMessageBox {{
                background-color: {w};
            }}
            QLabel {{
                color: {tp};
            }}
            QPushButton {{
                padding: 8px 16px;
                background-color: {a};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {ah};
            }}
        """

        cls._SETUP_SUCCESS_DIALOG = f"""
            QMessageBox {{
                background-color: {s};
                color: {tp};
            }}
            QLabel {{
                color: {tp};
            }}
            QPushButton {{
                padding: 8px 16px;
                background-color: {cls.SUCCESS};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {cls.SUCCESS_HOVER};
            }}
        """

    # ═══════════════════════════════════════════════════════════
    # Public constant maps (for runtime lookups)
    # ═══════════════════════════════════════════════════════════
    QSS_MAP = {}


# Build QSS strings eagerly so StyleSheet.MAIN etc. are plain strings at import time.
StyleSheet._build_all()
StyleSheet.MAIN = StyleSheet._MAIN
StyleSheet.PASTE_BUTTON = StyleSheet._PASTE_BUTTON
StyleSheet.ANALYZE_BUTTON = StyleSheet._ANALYZE_BUTTON
StyleSheet.PLAYLIST_BUTTON = StyleSheet._PLAYLIST_BUTTON
StyleSheet.FORMAT_TOGGLE_BUTTON = StyleSheet._FORMAT_TOGGLE_BUTTON
StyleSheet.CHECKBOX = StyleSheet._CHECKBOX
StyleSheet.PROGRESS_BAR = StyleSheet._PROGRESS_BAR
StyleSheet.STATUS_LABEL = StyleSheet._STATUS_LABEL
StyleSheet.OPEN_FOLDER_BUTTON = StyleSheet._OPEN_FOLDER_BUTTON
StyleSheet.SECONDARY_BUTTON = StyleSheet._SECONDARY_BUTTON
StyleSheet.WARNING_BUTTON = StyleSheet._WARNING_BUTTON
StyleSheet.DANGER_BUTTON = StyleSheet._DANGER_BUTTON
StyleSheet.UPDATE_DIALOG_MESSAGE = StyleSheet._UPDATE_DIALOG_MESSAGE
StyleSheet.UPDATE_DIALOG_CHANGELOG = StyleSheet._UPDATE_DIALOG_CHANGELOG
StyleSheet.UPDATE_DIALOG_DOWNLOAD_BTN = StyleSheet._UPDATE_DIALOG_DOWNLOAD_BTN
StyleSheet.UPDATE_DIALOG_REMIND_BTN = StyleSheet._UPDATE_DIALOG_REMIND_BTN
StyleSheet.UPDATE_DIALOG_MAIN = StyleSheet._UPDATE_DIALOG_MAIN
StyleSheet.FILE_EXISTS_DIALOG = StyleSheet._FILE_EXISTS_DIALOG
StyleSheet.SETUP_SUCCESS_DIALOG = StyleSheet._SETUP_SUCCESS_DIALOG
StyleSheet.QSS_MAP = {
    "MAIN": StyleSheet._MAIN,
    "PASTE_BUTTON": StyleSheet._PASTE_BUTTON,
    "ANALYZE_BUTTON": StyleSheet._ANALYZE_BUTTON,
    "PLAYLIST_BUTTON": StyleSheet._PLAYLIST_BUTTON,
    "FORMAT_TOGGLE_BUTTON": StyleSheet._FORMAT_TOGGLE_BUTTON,
    "CHECKBOX": StyleSheet._CHECKBOX,
    "PROGRESS_BAR": StyleSheet._PROGRESS_BAR,
    "STATUS_LABEL": StyleSheet._STATUS_LABEL,
    "OPEN_FOLDER_BUTTON": StyleSheet._OPEN_FOLDER_BUTTON,
    "UPDATE_DIALOG_MESSAGE": StyleSheet._UPDATE_DIALOG_MESSAGE,
    "UPDATE_DIALOG_CHANGELOG": StyleSheet._UPDATE_DIALOG_CHANGELOG,
    "UPDATE_DIALOG_DOWNLOAD_BTN": StyleSheet._UPDATE_DIALOG_DOWNLOAD_BTN,
    "UPDATE_DIALOG_REMIND_BTN": StyleSheet._UPDATE_DIALOG_REMIND_BTN,
    "UPDATE_DIALOG_MAIN": StyleSheet._UPDATE_DIALOG_MAIN,
    "FILE_EXISTS_DIALOG": StyleSheet._FILE_EXISTS_DIALOG,
    "SETUP_SUCCESS_DIALOG": StyleSheet._SETUP_SUCCESS_DIALOG,
    "SECONDARY_BUTTON": StyleSheet._SECONDARY_BUTTON,
    "WARNING_BUTTON": StyleSheet._WARNING_BUTTON,
    "DANGER_BUTTON": StyleSheet._DANGER_BUTTON,
}