"""Startup Profiling and Benchmark Script.

Executes the startup path and measures exact milliseconds spent at each stage.
"""

import sys
import os
import time

print("=" * 60)
print("LUXIOUS STARTUP BENCHMARK & DIAGNOSTIC")
print("=" * 60)

t0 = time.perf_counter()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

t_qt = time.perf_counter()
print(f"[STARTUP] PySide6 import: {t_qt - t0:.4f} s")

from ui.main_window import MainWindow
from ui.styles import MAIN_STYLESHEET

t_app_mod = time.perf_counter()
print(f"[STARTUP] UI modules import: {t_app_mod - t0:.4f} s")

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

app = QApplication(sys.argv)
app.setStyleSheet(MAIN_STYLESHEET)
t_app = time.perf_counter()
print(f"[STARTUP] QApplication created: {t_app - t0:.4f} s")

print(f"[STARTUP] Creating MainWindow...")
t_win_start = time.perf_counter()
window = MainWindow()
t_win_end = time.perf_counter()
print(f"[STARTUP] MainWindow created: {t_win_end - t0:.4f} s (took {(t_win_end - t_win_start)*1000:.1f} ms)")

print(f"[STARTUP] Showing MainWindow...")
t_show_start = time.perf_counter()
window.show()
t_show_end = time.perf_counter()
print(f"[STARTUP] MainWindow shown: {t_show_end - t0:.4f} s (took {(t_show_end - t_show_start)*1000:.1f} ms)")

print("=" * 60)
print(f"TOTAL TIME TO WINDOW DISPLAY: {t_show_end - t0:.4f} s")
print("=" * 60)

# Process events for 200ms to test first event loop cycle
QTimer.singleShot(300, app.quit)
app.exec()
print(f"[STARTUP] First event loop cycle completed: {time.perf_counter() - t0:.4f} s")
