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

            with TemporaryDirectory(prefix="lumination-build-check-") as temporary:
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
