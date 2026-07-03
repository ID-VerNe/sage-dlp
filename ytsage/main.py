import os
import sys

# --- Embedded Python Tcl/Tk Fix (must be before any GUI imports) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))         # ytsage/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                      # project root (contains python_embed/)
EMBED_TCL_DIR = os.path.join(PROJECT_ROOT, "python_embed", "Lib", "site-packages", "tcl")
if os.path.exists(EMBED_TCL_DIR):
    os.environ["TCL_LIBRARY"] = os.path.join(EMBED_TCL_DIR, "tcl8.6")
    os.environ["TK_LIBRARY"] = os.path.join(EMBED_TCL_DIR, "tk8.6")
# ------------------------------------------------------------------

from PySide6.QtWidgets import QApplication, QMessageBox

from .utils.ytsage_logger import logger
from .gui.ytsage_gui_main import YTSageApp  # Import the main application class from ytsage_gui_main


def show_error_dialog(message):
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setText("Application Error")
    error_dialog.setInformativeText(message)
    error_dialog.setWindowTitle("Error")
    error_dialog.exec()


def main():
    try:
        logger.info("Starting YTSage application")
        app = QApplication(sys.argv)

        window = YTSageApp()  # Instantiate the main application class
        window.show()
        logger.info("Application window shown, entering main loop")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Critical application error: {e}", exc_info=True)
        show_error_dialog(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
