"""Lumination Desktop Application Entry Point.

Starts the PySide6 application event loop, applies visual styling,
configures global crash logging, and displays the primary survey window.
"""

from __future__ import annotations
import sys
import os
import time
import traceback
from datetime import datetime

# Startup timing tracker
_T_START = time.perf_counter()
_DEBUG_STARTUP = os.environ.get("LUMINATION_DEBUG_STARTUP", "0") == "1" or "--debug-startup" in sys.argv

def log_startup(stage: str) -> None:
    if _DEBUG_STARTUP:
        elapsed = time.perf_counter() - _T_START
        print(f"[STARTUP] {stage}: {elapsed:.4f} s", flush=True)

log_startup("Python entry point")

# Add project root to sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configure Matplotlib fonts safely before any canvas creation
os.environ["MPLBACKEND"] = "QtAgg"

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
log_startup("PySide6 imported")

from ui.main_window import MainWindow
from ui.styles import MAIN_STYLESHEET
log_startup("Application modules imported")


def setup_crash_logger() -> None:
    """Setup top-level unhandled exception hook that logs crashes cleanly to a file."""
    def _unhandled_exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Determine log file location in local AppData or next to exe
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        log_dir = os.path.join(appdata, "Lumination")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "lumination_crash.log")

        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        timestamp = datetime.now().isoformat()

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*70}\nCRASH REPORT: {timestamp}\n{'='*70}\n{err_msg}\n")
        except Exception:
            pass

        # Try to show a readable message box if QApplication is active
        try:
            app = QApplication.instance()
            if app:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Lumination - Application Error")
                msg.setText("An unexpected error occurred in Lumination.")
                msg.setInformativeText(f"A detailed crash report has been saved to:\n{log_path}\n\nError: {exc_value}")
                msg.setDetailedText(err_msg)
                msg.exec()
        except Exception:
            pass

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _unhandled_exception_hook


def main() -> int:
    """Launch Lumination Desktop Application."""
    setup_crash_logger()
    log_startup("main() entered")

    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Lumination")
    app.setOrganizationName("Lumination Photometrics")
    app.setStyleSheet(MAIN_STYLESHEET)
    log_startup("QApplication created and styled")

    log_startup("Creating MainWindow")
    window = MainWindow()
    log_startup("MainWindow created")

    log_startup("Showing MainWindow")
    window.show()
    t_visible = time.perf_counter() - _T_START
    log_startup(f"MainWindow visible ({t_visible:.4f} s)")

    if "--smoke-test" in sys.argv:
        from utils.build_smoke import run_smoke_test
        index = sys.argv.index("--smoke-test")
        if index + 1 >= len(sys.argv):
            return 2
        return run_smoke_test(app, window, sys.argv[index + 1])

    # Event loop responsive callback
    def _on_event_loop_ready() -> None:
        t_responsive = time.perf_counter() - _T_START
        dt_response = t_responsive - t_visible
        log_startup(f"Main window visible and event loop responsive: {t_responsive:.4f} s (event latency: {dt_response*1000:.1f} ms)")

    QTimer.singleShot(0, _on_event_loop_ready)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
