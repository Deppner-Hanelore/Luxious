"""Phase 2: the chosen language applies everywhere, is remembered, and reaches the outputs."""

import tempfile

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from i18n.strings import STRINGS
from i18n.translations import (
    SETTINGS_KEY,
    TRANSLATIONS,
    TranslationManager,
    display_note,
    tr,
    use_language,
)
from models.project import LuminationProject
from models.room import Room


def _project():
    project = LuminationProject(name="Lang", room=Room(length=6.0, width=4.0, wall_margin=0.5))
    project.regenerate_grid(rows=2, cols=3, wall_margin=0.5)
    for index, point in enumerate(project.points):
        point.record_reading(300.0 + 20 * index)
    return project


def _window(tmp_path, project=None):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    window = MainWindow(project or _project(), recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    return window


def _close(window):
    window.project.is_dirty = False
    window.recovery_store.discard()
    window.close()


def test_every_catalog_entry_has_three_languages():
    for key, values in STRINGS.items():
        assert len(values) == 3 and all(values), key
        for code, text in zip(("en", "ro", "de"), values):
            assert TRANSLATIONS[code][key] == text


def test_language_choice_is_saved_and_restored(qapp):
    manager = TranslationManager.get_instance()
    manager.set_language("ro")
    assert QSettings().value(SETTINGS_KEY) == "ro"
    manager.set_language("en", persist=False)
    assert manager.load_saved_language() == "ro"
    store = QSettings(tempfile.mktemp(suffix=".ini"), QSettings.Format.IniFormat)
    store.setValue(SETTINGS_KEY, "de")
    assert manager.load_saved_language(store) == "de"
    store.setValue(SETTINGS_KEY, "xx")
    manager.set_language("en", persist=False)
    assert manager.load_saved_language(store) == "en"
    QSettings().remove(SETTINGS_KEY)


def test_window_starts_in_saved_language_including_start_screen(qapp, tmp_path):
    TranslationManager.get_instance().set_language("ro", persist=False)
    from ui.main_window import MainWindow
    from persistence.recovery import RecoveryStore

    window = MainWindow(recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    assert window.content_stack.currentWidget() is window.start_screen
    assert window.start_screen.btn_new.text() == "Măsurătoare nouă"
    assert window.start_screen.lbl_title.text() == tr("start_title", "ro")
    assert window.menu_file.title() == "&Fișier"
    window.close()


@pytest.mark.parametrize("code", ["ro", "de"])
def test_switching_language_updates_open_window(qapp, tmp_path, code):
    window = _window(tmp_path)
    window.show()
    window.btn_toggle_left.click()
    window.btn_toggle_right.click()
    QApplication.processEvents()
    TranslationManager.get_instance().set_language(code, persist=False)
    QApplication.processEvents()
    with use_language(code):
        expected = {
            "survey menu": (window.menu_survey.title(), "&" + tr("menu_survey")),
            "grid action": (window.act_generate_grid.text(), tr("menu_change_grid")),
            "survey bar": (window.survey_widget.btn_next_unmeasured.text(), tr("survey_next_unmeasured")),
            "source label": (window.survey_widget.lbl_source_mode.text(), tr("survey_manual_entry")),
            "layer": (window.layer_widget.chk_grid.text(), tr("layers_grid")),
            "layer group": (window.layer_widget.layer_group.title(), tr("layers_group")),
            "interp item": (window.layer_widget.combo_interp.itemText(0), tr("layers_interp_linear")),
            "target group": (window.target_panel.group.title(), tr("target_group")),
            "comparison": (window.comparison_panel.rb_measured.text(), tr("cmp_rb_measured")),
            "map tooltip": (window.canvas_widget.btn_add_point.toolTip(), tr("canvas_tip_add_point")),
            "save status": (window.lbl_save_status.text(), tr(window._save_status_key)),
            "toggle tip": (window.btn_toggle_left.toolTip(), tr("mw_tip_toggle_left")),
        }
    for name, (actual, wanted) in expected.items():
        assert actual == wanted, name
    assert window.table_widget.model.headerData(3, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Orientation.Horizontal) == tr("col_lux", code)
    _close(window)


def test_app_generated_notes_show_in_active_language():
    with use_language("ro"):
        assert display_note("Grid (Col 2, Row 3)") == "Grilă (coloana 2, rândul 3)"
        assert display_note("Custom Sensor") == tr("note_custom_sensor")
        assert display_note("near the window") == "near the window"


def test_use_language_restores_previous_language():
    manager = TranslationManager.get_instance()
    before = manager.current_language
    with use_language("de"):
        assert tr("menu_file") == "Datei"
    assert manager.current_language == before


def test_project_remembers_language_it_was_saved_in(qapp, tmp_path):
    from persistence.project_io import load_project

    window = _window(tmp_path)
    TranslationManager.get_instance().set_language("de", persist=False)
    window.project.file_path = str(tmp_path / "p.luxproj")
    assert window._on_save_project()
    assert load_project(window.project.file_path).language == "de"
    _close(window)


def test_pdf_report_is_written_in_requested_language_with_unicode_font(tmp_path):
    from reporting.pdf_report import generate_pdf_report

    project = _project()
    project.target_lux = 500.0
    path = tmp_path / "ro.pdf"
    generate_pdf_report(project, str(path), lang="ro")
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"SegoeUI" in data or b"DejaVuSans" in data  # a Unicode font is embedded, so ă, ș, ț render
    assert TranslationManager.get_instance().current_language == "en"


def test_qt_builtin_texts_have_romanian_fallback(qapp):
    import main

    main._install_qt_translator(qapp, "ro")
    try:
        assert qapp.translate("QLineEdit", "&Copy") == "&Copiază"
        assert qapp.translate("QDockWidget", "Close") == "Închide"
    finally:
        main._install_qt_translator(qapp, "en")
    assert qapp.translate("QLineEdit", "&Copy") == "&Copy"


def test_app_is_named_luxious_everywhere_visible(qapp, tmp_path):
    from utils.app_info import APP_NAME

    assert APP_NAME == "Luxious"
    window = _window(tmp_path)
    assert window.windowTitle().startswith("Luxious")
    assert window.act_about.text() == "About Luxious"
    assert "Luxious" in tr("help_shortcuts_heading", app=APP_NAME)
    _close(window)


def test_settings_saved_under_old_name_are_carried_over_once(tmp_path):
    import main

    legacy = QSettings(str(tmp_path / "old.ini"), QSettings.Format.IniFormat)
    legacy.setValue("ui/language", "ro")
    legacy.setValue("last_project_path", "C:/old.luxproj")
    current = QSettings(str(tmp_path / "new.ini"), QSettings.Format.IniFormat)
    current.setValue("last_project_path", "C:/kept.luxproj")
    main._carry_over_legacy_settings(current, legacy)
    assert current.value("ui/language") == "ro"
    assert current.value("last_project_path") == "C:/kept.luxproj"
    legacy.setValue("ui/language", "de")
    main._carry_over_legacy_settings(current, legacy)
    assert current.value("ui/language") == "ro"
