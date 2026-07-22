import os
import sys

# --- Embedded Python Tcl/Tk Fix (must be before any GUI imports) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))         # sage_dlp/
PROJECT_ROOT = os.path.dirname(BASE_DIR)                      # project root (contains python_embed/)
EMBED_TCL_DIR = os.path.join(PROJECT_ROOT, "python_embed", "Lib", "site-packages", "tcl")
if os.path.exists(EMBED_TCL_DIR):
    os.environ["TCL_LIBRARY"] = os.path.join(EMBED_TCL_DIR, "tcl8.6")
    os.environ["TK_LIBRARY"] = os.path.join(EMBED_TCL_DIR, "tk8.6")
# ------------------------------------------------------------------

# Ensure the package root is on sys.path for absolute imports.
# Needed when running as a script directly (python sage_dlp/main.py)
# or when frozen by PyInstaller (relative imports fail in both cases).
if not __package__ or getattr(sys, "frozen", False):
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication, QMessageBox

from sage_dlp.utils.sage_logger import logger
from sage_dlp.gui.sage_gui_main import SageApp  # Import the main application class from sage_gui_main


def show_error_dialog(message):
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setText("Application Error")
    error_dialog.setInformativeText(message)
    error_dialog.setWindowTitle("Error")
    error_dialog.exec()


# @lat: [[Project]]

def main():
    try:
        logger.info("Starting SageDLP application")
        app = QApplication(sys.argv)

        window = SageApp()  # Instantiate the main application class
        window.show()
        logger.info("Application window shown, entering main loop")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Critical application error: {e}", exc_info=True)
        show_error_dialog(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
