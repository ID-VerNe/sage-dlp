"""
Daylight (Light) Theme Stylesheet for YTSage.
Clean, modern white theme with subtle blue accents.
"""

class StyleSheet:
    MAIN = """
            QMainWindow {
                background-color: #f5f6fa;
            }
            QWidget {
                background-color: #f5f6fa;
                color: #1a1a2e;
            }
            QLineEdit {
                padding: 5px 15px;
                border: 2px solid #78909c;
                border-radius: 6px;
                background-color: #ffffff;
                color: #1a1a2e;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0984e3;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0984e3;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0773c5;
            }
            QPushButton:pressed {
                background-color: #065ba0;
                padding: 10px 13px 6px 17px;
            }
            QPushButton:disabled {
                background-color: #b0bec5;
                color: #ffffff;
            }
            QTableWidget {
                border: 2px solid #78909c;
                border-radius: 4px;
                background-color: #ffffff;
                gridline-color: #b0bec5;
            }
            QHeaderView::section {
                background-color: #e0e4eb;
                padding: 5px;
                border: 1px solid #b0bec5;
                color: #1a1a2e;
                font-weight: bold;
            }
            QProgressBar {
                border: 2px solid #78909c;
                border-radius: 4px;
                text-align: center;
                color: #1a1a2e;
                background-color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #00b894;
                border-radius: 2px;
            }
            QLabel {
                color: #1a1a2e;
            }
            /* Style for filter buttons */
            QPushButton.filter-btn {
                background-color: #ffffff;
                padding: 5px 10px;
                margin: 0 5px;
                border: 1px solid #b0bec5;
                color: #1a1a2e;
            }
            QPushButton.filter-btn:checked {
                background-color: #0984e3;
                color: white;
                border-color: #0984e3;
            }
            QPushButton.filter-btn:hover {
                background-color: #d0e4fa;
                border-color: #0984e3;
            }
            QPushButton.filter-btn:checked:hover {
                background-color: #0773c5;
            }
            /* Modern Scrollbar Styling */
            QScrollBar:vertical {
                border: none;
                background: #f5f6fa;
                width: 14px;
                margin: 15px 0 15px 0;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #b0bec5;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #546e7a;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: #f5f6fa;
                height: 15px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: #f5f6fa;
                height: 15px;
                border-bottom-left-radius: 7px;
                border-bottom-right-radius: 7px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical:hover,
            QScrollBar::add-line:vertical:hover {
                background: #b0bec5;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
    """

    PASTE_BUTTON = """
            QPushButton {
                padding: 9px 20px;
                background-color: #ffffff;
                border: 2px solid #78909c;
                border-radius: 5px;
                color: #1a1a2e;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #d0e4fa;
                border-color: #0984e3;
            }
            QPushButton:pressed {
                background-color: #d0e4fa;
                padding: 11px 18px 7px 22px;
            }
    """

    ANALYZE_BUTTON = """
            QPushButton {
                padding: 9px 20px;
                background-color: #00b894;
                border: none;
                border-radius: 5px;
                color: white;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00a381;
            }
            QPushButton:pressed {
                background-color: #008e6f;
                padding: 11px 18px 7px 22px;
            }
            QPushButton:disabled {
                background-color: #b0bec5;
                color: #ffffff;
            }
    """

    PLAYLIST_BUTTON = """
            QPushButton {
                padding: 6px 12px;
                background-color: #ffffff;
                border: 1px solid #0984e3;
                border-radius: 4px;
                color: #0984e3;
                font-weight: normal;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background-color: #d0e4fa;
                border-color: #0773c5;
            }
            QPushButton:pressed {
                background-color: #d0e4fa;
                padding: 8px 10px 4px 12px;
            }
    """

    FORMAT_TOGGLE_BUTTON = """
            QPushButton {
                padding: 8px 15px;
                background-color: #ffffff;
                border: 1px solid #78909c;
                border-radius: 4px;
                color: #1a1a2e;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #0984e3;
                color: white;
                border-color: #0984e3;
            }
            QPushButton:hover {
                background-color: #d0e4fa;
                border-color: #0984e3;
            }
            QPushButton:checked:hover {
                background-color: #0773c5;
            }
            QPushButton:pressed {
                background-color: #d0e4fa;
                padding: 10px 13px 6px 17px;
            }
            QPushButton:checked:pressed {
                background-color: #065ba0;
                padding: 10px 13px 6px 17px;
            }
    """

    CHECKBOX = """
            QCheckBox {
                color: #1a1a2e;
                padding: 5px;
                margin-left: 20px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #78909c;
                background: #ffffff;
                border-radius: 9px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0984e3;
                background: #0984e3;
                border-radius: 9px;
            }
             QCheckBox:disabled { color: #78909c; }
             QCheckBox::indicator:disabled { border-color: #b0bec5; background: #e0e4eb; }
    """

    PROGRESS_BAR = """
            QProgressBar {
                border: 2px solid #78909c;
                border-radius: 4px;
                text-align: center;
                color: #1a1a2e;
                background-color: #ffffff;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #00b894;
                border-radius: 2px;
            }
    """

    STATUS_LABEL = """
            QLabel {
                color: #37474f;
                font-size: 12px;
                padding: 5px;
            }
    """

    OPEN_FOLDER_BUTTON = """
            QPushButton {
                background-color: #ffffff;
                color: #37474f;
                border: 1px solid #78909c;
                border-radius: 5px;
                font-size: 16px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #d0e4fa;
                border: 1px solid #0984e3;
            }
            QPushButton:pressed {
                background-color: #d0e4fa;
                padding: 4px 0px 0px 4px;
            }
    """

    UPDATE_DIALOG_MESSAGE = """
            QLabel {
                background-color: #ffffff;
                border: 1px solid #78909c;
                border-radius: 6px;
                padding: 15px;
                margin: 5px 0;
                color: #1a1a2e;
            }
    """

    UPDATE_DIALOG_CHANGELOG = """
            QTextEdit {
                background-color: #ffffff;
                border: 2px solid #78909c;
                border-radius: 6px;
                color: #1a1a2e;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f6fa;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #b0bec5;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #546e7a;
            }
    """

    UPDATE_DIALOG_DOWNLOAD_BTN = """
            QPushButton {
                padding: 10px 20px;
                background-color: #0984e3;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 13px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #0773c5;
            }
            QPushButton:pressed {
                background-color: #065ba0;
            }
    """

    UPDATE_DIALOG_REMIND_BTN = """
            QPushButton {
                padding: 10px 20px;
                background-color: #ffffff;
                border: 1px solid #546e7a;
                border-radius: 6px;
                color: #1a1a2e;
                font-weight: bold;
                font-size: 13px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #e0e4eb;
                border-color: #37474f;
            }
            QPushButton:pressed {
                background-color: #dde2e8;
            }
    """

    UPDATE_DIALOG_MAIN = """
            QDialog {
                background-color: #f5f6fa;
                border: 1px solid #78909c;
                border-radius: 8px;
            }
            QLabel {
                color: #1a1a2e;
                font-size: 12px;
            }
    """

    FILE_EXISTS_DIALOG = """
            QMessageBox {
                background-color: #ffffff;
            }
            QLabel {
                color: #1a1a2e;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #0984e3;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0773c5;
            }
    """

    SETUP_SUCCESS_DIALOG = """
            QMessageBox {
                background-color: #f5f6fa;
                color: #1a1a2e;
            }
            QLabel {
                color: #1a1a2e;
            }
            QPushButton {
                padding: 8px 15px;
                background-color: #00b894;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00a381;
            }
    """