"""Phase 4: start screen and new-survey window show only Language; File menu and Save As."""

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from i18n.translations import TranslationManager, tr
from models.project import LuminationProject
from models.room import Room


def _window(tmp_path, project=None):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    return MainWindow(project, recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                      settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))


def _visible_menus(window):
    return [a.text() for a in window.menuBar().actions() if a.isVisible()]


def _project():
    project = LuminationProject(name="Menus", room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
    return project


def test_start_screen_shows_only_language_menu(qapp, tmp_path):
    window = _window(tmp_path)
    assert window.content_stack.currentWidget() is window.start_screen
    assert _visible_menus(window) == [window.menu_lang.title()]
    TranslationManager.get_instance().set_language("de", persist=False)
    assert _visible_menus(window) == [window.menu_lang.title()] == ["&Sprache"]
    window.close()


def test_open_survey_shows_full_file_menu(qapp, tmp_path):
    window = _window(tmp_path, _project())
    assert len(_visible_menus(window)) == 4
    texts = [a.text() for a in window.menu_file.actions() if not a.isSeparator()]
    assert texts == [window.act_new.text(), window.act_open.text(), window.act_save.text(),
                     window.act_save_as.text(), window.act_exit.text()]
    assert all(a.isEnabled() for a in (window.act_new, window.act_open, window.act_save, window.act_save_as, window.act_exit))
    window.project.is_dirty = False
    window.close()


def test_new_survey_window_shows_only_language_and_switches_live(qapp, tmp_path, monkeypatch):
    from ui.dialogs.survey_setup_dialog import SurveySetupDialog

    window = _window(tmp_path, _project())
    seen = {}

    def run(dialog):
        seen["menus"] = _visible_menus(window)
        seen["dialog_menus"] = [a.text() for a in dialog.menu_bar.actions()]
        TranslationManager.get_instance().set_language("ro", persist=False)
        seen["title"] = dialog.windowTitle()
        seen["next"] = dialog.next_button.text()
        seen["label"] = dialog.room_form.labelForField(dialog.length).text()
        return int(SurveySetupDialog.DialogCode.Rejected)

    monkeypatch.setattr(SurveySetupDialog, "exec", run)
    window._on_new_project()
    assert seen["menus"] == ["&Language"]
    assert seen["dialog_menus"] == [tr("menu_language", "en")]
    assert seen["title"] == tr("setup_title", "ro")
    assert seen["next"] == tr("setup_next", "ro")
    assert seen["label"] == tr("setup_length", "ro")
    assert len(_visible_menus(window)) == 4
    window.project.is_dirty = False
    window.close()


def test_save_as_offers_project_csv_and_pdf(qapp, tmp_path, monkeypatch):
    window = _window(tmp_path, _project())
    captured = {}

    def fake(_parent, _title, default, filters):
        captured["filters"] = filters.split(";;")
        captured["default"] = default
        return (str(tmp_path / "report"), filters.split(";;")[3])

    monkeypatch.setattr("ui.main_window.QFileDialog.getSaveFileName", fake)
    window.act_save_as.trigger()
    assert captured["filters"] == [tr("filter_project", app="Luxious"), tr("filter_csv"), tr("filter_excel"), tr("filter_pdf"), tr("filter_png")]
    assert (tmp_path / "report.pdf").exists()
    assert window.project.file_path is None
    window.project.is_dirty = False
    window.close()
