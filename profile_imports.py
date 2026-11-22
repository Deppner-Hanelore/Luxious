"""Profile individual module imports."""

import time

modules = [
    "PySide6.QtWidgets",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "numpy",
    "scipy",
    "scipy.interpolate",
    "matplotlib",
    "matplotlib.pyplot",
    "matplotlib.backends.backend_qtagg",
    "reportlab",
    "pandas",
    "models.measurement",
    "models.room",
    "models.project",
    "analysis.statistics",
    "analysis.interpolation",
    "analysis.contours",
    "analysis.comparison",
    "visualization.color_maps",
    "visualization.map_plotter",
    "visualization.chart_plotter",
    "persistence.project_io",
    "persistence.csv_io",
    "reporting.pdf_report",
    "reporting.chart_exporter",
    "ui.styles",
    "ui.room_canvas",
    "ui.measurement_table",
    "ui.results_panel",
    "ui.target_panel",
    "ui.comparison_panel",
    "ui.layer_control_widget",
    "ui.dialogs.new_project_dialog",
    "ui.dialogs.grid_generator_dialog",
    "ui.dialogs.point_edit_dialog",
    "ui.dialogs.export_dialog",
    "ui.main_window",
]

print("INDIVIDUAL IMPORT TIMINGS:")
for mod in modules:
    t0 = time.perf_counter()
    __import__(mod)
    dt = (time.perf_counter() - t0) * 1000
    if dt > 10.0:  # Only print things taking > 10ms
        print(f"  {mod:35s}: {dt:6.1f} ms")
