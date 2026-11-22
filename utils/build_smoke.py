"""Exercise essential features inside the actual frozen desktop executable."""
from __future__ import annotations

import json
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, QTimer

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow


def run_smoke_test(app: QApplication, window: MainWindow, report_path: str) -> int:
    """Run once through the Qt event loop, write JSON, and exit without prompts."""
    report = Path(report_path).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)

    def check() -> None:
        checks: list[str] = []
        exit_code = 1
        result: dict[str, object] = {"success": False, "checks": checks}
        try:
            from models.measurement import MeasurementPoint
            from models.project import LuminationProject
            from models.room import Room
            from persistence.csv_io import export_measurements_to_csv
            from persistence.project_io import load_project, save_project
            from persistence.recovery import RecoveryStore
            from reporting.chart_exporter import export_room_map_image
            from reporting.pdf_report import generate_pdf_report

            with TemporaryDirectory(prefix="luxious-build-check-") as temporary:
                root = Path(temporary)
                window.recovery_store = RecoveryStore(str(root / "recovery.json"))
                window.settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
                project = LuminationProject(name="Build check", room=Room(length=4, width=3))
                project.points = [
                    MeasurementPoint(id="P1", x=1, y=1),
                    MeasurementPoint(id="P2", x=3, y=1),
                    MeasurementPoint(id="P3", x=1, y=2),
                ]
                window._replace_project(project)
                window._show_workspace()
                checks.append("Qt window and survey controls")
                for point_id, value in [("P1", 0), ("P2", 200), ("P3", 400)]:
                    window._on_point_selected(point_id)
                    window.survey_widget.edit_lux.setText(str(value))
                    window.survey_widget.btn_save_next.click()
                if [p.lux for p in project.points] != [0, 200, 400]:
                    raise RuntimeError("The packaged survey controls did not record the expected values.")
                checks.append("Manual recording, including zero")
                window.canvas_widget.canvas.draw()
                if window.interp_result is None or not window.interp_result.success:
                    raise RuntimeError("The packaged numerical reconstruction failed.")
                checks.append("SciPy reconstruction and Qt map rendering")
                save_project(project, str(root / "survey.luxproj"))
                restored = load_project(str(root / "survey.luxproj"))
                if [p.lux for p in restored.points] != [0, 200, 400]:
                    raise RuntimeError("Saved project did not round-trip correctly.")
                checks.append("Project save and reload")
                export_measurements_to_csv(project, str(root / "survey.csv"))
                generate_pdf_report(project, str(root / "survey.pdf"))
                export_room_map_image(project, output_path=str(root / "survey.png"), dpi=80)
                for filename in ("survey.csv", "survey.pdf", "survey.png"):
                    if (root / filename).stat().st_size == 0:
                        raise RuntimeError(f"Empty export: {filename}")
                checks.append("CSV, PDF, and PNG exports")

                # Grid tables (Excel and CSV) are read back exactly as written.
                from persistence.comparison_io import apply_comparison
                from persistence.table_io import project_from_table, read_table, write_table
                grid_project = LuminationProject(name="Table check", room=Room(length=6, width=4, wall_margin=0.5))
                grid_project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
                for index, point in enumerate(grid_project.points):
                    point.record_reading(300.0 + 10 * index)
                for suffix in (".xlsx", ".csv"):
                    write_table(grid_project, str(root / f"table{suffix}"))
                    values = read_table(str(root / f"table{suffix}"))
                    reopened = project_from_table(values, "Reopened", 2.5, 3.0, 0.5)
                    if sorted(p.lux for p in reopened.points) != sorted(p.lux for p in grid_project.points):
                        raise RuntimeError(f"The {suffix} table did not round-trip correctly.")
                checks.append("Excel and CSV tables")

                # Comparison with a file, and a Romanian PDF with Unicode text.
                compared = grid_project
                apply_comparison(compared, str(root / "table.xlsx"))
                from reporting.pdf_report import generate_pdf_report as _pdf
                _pdf(compared, str(root / "raport.pdf"), lang="ro")
                if (root / "raport.pdf").stat().st_size == 0:
                    raise RuntimeError("Empty Romanian PDF")
                checks.append("Comparison and Romanian PDF")
                project.is_dirty = False
            result["success"] = True
            exit_code = 0
        except Exception:
            result["error"] = traceback.format_exc()
        finally:
            window.project.is_dirty = False
            try:
                report.write_text(json.dumps(result, indent=2), encoding="utf-8")
            finally:
                app.exit(exit_code)

    QTimer.singleShot(0, check)
    return app.exec()
