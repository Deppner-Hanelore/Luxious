"""Luxious Desktop Application Entry Point.

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
from utils.app_info import APP_NAME, ORGANIZATION_NAME, LEGACY_APP_NAME, LEGACY_ORGANIZATION_NAME
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
        log_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "luxious_crash.log")

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
                from i18n.translations import tr
                msg.setWindowTitle(f"{APP_NAME} - {tr('crash_title')}")
                msg.setText(tr("crash_text", app=APP_NAME))
                msg.setInformativeText(tr("crash_info", path=log_path, error=exc_value))
                msg.setDetailedText(err_msg)
                msg.exec()
        except Exception:
            pass

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _unhandled_exception_hook


_qt_translators = []

# Qt texts shown in this app (dock buttons, tab scroll buttons, text-field menus) mapped to
# our own catalog, used when Qt ships no translation file for the language (Romanian).
_QT_TEXT_KEYS = {
    "Close": "qt_close",
    "Float": "qt_float",
    "Scroll Left": "qt_scroll_left",
    "Scroll Right": "qt_scroll_right",
    "&Undo": "qt_undo",
    "&Redo": "qt_redo",
    "Cu&t": "qt_cut",
    "&Copy": "qt_copy",
    "&Paste": "qt_paste",
    "Delete": "qt_delete",
    "Select All": "qt_select_all",
    "&Step up": "qt_step_up",
    "Step &down": "qt_step_down",
}


def _install_qt_translator(app, language: str) -> None:
    """Translate Qt's own texts: Qt's translation file when one exists, our catalog otherwise."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from i18n.translations import tr

    for old in _qt_translators:
        app.removeTranslator(old)
    _qt_translators.clear()
    if language == "en":
        return

    class _CatalogTranslator(QTranslator):
        def translate(self, context, source_text, disambiguation=None, n=-1):
            key = _QT_TEXT_KEYS.get(source_text)
            return tr(key, language) if key else ""

        def isEmpty(self) -> bool:
            return False

    fallback = _CatalogTranslator(app)
    app.installTranslator(fallback)
    _qt_translators.append(fallback)
    official = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if official.load(QLocale(language), "qtbase", "_", path):
        app.installTranslator(official)  # installed last, so it is asked first
        _qt_translators.append(official)


def _carry_over_legacy_settings(settings=None, legacy=None) -> None:
    """Copy settings and the recovery copy saved under the former name "Lumination" (once)."""
    import shutil
    from PySide6.QtCore import QSettings, QStandardPaths

    settings = settings if settings is not None else QSettings()
    if settings.value("migrated_from_lumination", False, type=bool):
        return
    legacy = legacy if legacy is not None else QSettings(LEGACY_ORGANIZATION_NAME, LEGACY_APP_NAME)
    for key in legacy.allKeys():
        if not settings.contains(key):
            settings.setValue(key, legacy.value(key))
    settings.setValue("migrated_from_lumination", True)
    settings.sync()

    new_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not new_dir:
        return
    # AppDataLocation is <base>/<organization>/<application>.
    base = os.path.dirname(os.path.dirname(new_dir))
    old_recovery = os.path.join(base, LEGACY_ORGANIZATION_NAME, LEGACY_APP_NAME, "recovery.json")
    new_recovery = os.path.join(new_dir, "recovery.json")
    try:
        if os.path.isfile(old_recovery) and not os.path.exists(new_recovery):
            os.makedirs(new_dir, exist_ok=True)
            shutil.copy2(old_recovery, new_recovery)
    except OSError:
        pass


def main() -> int:
    """Launch the Luxious desktop application."""
    setup_crash_logger()
    log_startup("main() entered")

    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    _carry_over_legacy_settings()
    app.setStyleSheet(MAIN_STYLESHEET)
    # Window and taskbar icon; inside the packaged exe the files live in PyInstaller's folder.
    icon_path = os.path.join(getattr(sys, "_MEIPASS", ROOT_DIR), "assets", "luxious.ico")
    if os.path.isfile(icon_path):
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))
    log_startup("QApplication created and styled")

    # Start in the language chosen in the previous session, before any window exists.
    from i18n.translations import TranslationManager
    manager = TranslationManager.get_instance()
    manager.load_saved_language()
    _install_qt_translator(app, manager.current_language)
    manager.language_changed.connect(lambda code: _install_qt_translator(app, code))

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
