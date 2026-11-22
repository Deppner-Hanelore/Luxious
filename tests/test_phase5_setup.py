"""Phase 5: remembered new-survey choices and outer points at the wall distance."""

import pytest
from PySide6.QtCore import QSettings

from models.room import Room
from ui.dialogs.survey_setup_dialog import SurveySetupDialog


def _settings(tmp_path):
    return QSettings(str(tmp_path / "defaults.ini"), QSettings.Format.IniFormat)


def test_choices_are_remembered_for_the_next_survey_except_the_name(qapp, tmp_path):
    store = _settings(tmp_path)
    first = SurveySetupDialog(settings=store)
    first.name.setText("Office 12")
    first.author.setText("Ana")
    first.length.setValue(8.0)
    first.width.setValue(5.5)
    first.grid_mode.setCurrentIndex(first.grid_mode.findData("spacing"))
    first.spacing_x.setValue(1.5)
    first.spacing_y.setValue(1.25)
    first.margin.setValue(0.75)
    first.traversal.setCurrentIndex(first.traversal.findData("left_to_right"))
    first.pages.setCurrentIndex(2)
    first._next()  # "Create survey" saves the choices
    assert first.result() == SurveySetupDialog.DialogCode.Accepted

    second = SurveySetupDialog(settings=store)
    assert second.name.text() != "Office 12"
    assert second.author.text() == "Ana"
    assert (second.length.value(), second.width.value(), second.margin.value()) == (8.0, 5.5, 0.75)
    assert second.grid_mode.currentData() == "spacing"
    assert (second.spacing_x.value(), second.spacing_y.value()) == (1.5, 1.25)
    assert second.spacing_x.isEnabled() and not second.cols.isEnabled()
    assert second.traversal.currentData() == "left_to_right"


def test_cancelled_window_does_not_change_the_defaults(qapp, tmp_path):
    store = _settings(tmp_path)
    dialog = SurveySetupDialog(settings=store)
    dialog.length.setValue(12.0)
    dialog.reject()
    assert SurveySetupDialog(settings=store).length.value() == 6.0


def test_outer_points_sit_exactly_at_the_wall_distance():
    room = Room(length=6.0, width=4.0, wall_margin=0.5)
    points = room.generate_grid_points(mode="count", rows=3, cols=4, wall_margin=0.5)
    xs = sorted({p.x for p in points})
    ys = sorted({p.y for p in points})
    assert xs[0] == pytest.approx(0.5) and xs[-1] == pytest.approx(5.5)
    assert ys[0] == pytest.approx(0.5) and ys[-1] == pytest.approx(3.5)
    spaced = room.generate_grid_points(mode="spacing", spacing_x=1.0, spacing_y=1.0, wall_margin=0.5)
    assert sorted({p.x for p in spaced}) == pytest.approx([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    assert sorted({p.y for p in spaced}) == pytest.approx([0.5, 1.5, 2.5, 3.5])


@pytest.mark.parametrize("mode", ["count", "spacing"])
def test_only_the_chosen_pair_of_fields_is_usable(qapp, tmp_path, mode):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    dialog = SurveySetupDialog(settings=_settings(tmp_path))
    dialog.grid_mode.setCurrentIndex(dialog.grid_mode.findData(mode))
    dialog.pages.setCurrentIndex(1)
    dialog.show()
    active, inactive = (
        ((dialog.cols, dialog.rows), (dialog.spacing_x, dialog.spacing_y))
        if mode == "count"
        else ((dialog.spacing_x, dialog.spacing_y), (dialog.cols, dialog.rows))
    )
    for field in active:
        assert field.isEnabled() and dialog.points_form.labelForField(field).isEnabled()
    for field in inactive:
        assert not field.isEnabled() and not dialog.points_form.labelForField(field).isEnabled()
        before = field.value()
        QTest.mouseClick(field, Qt.MouseButton.LeftButton)
        QTest.keyClicks(field, "9")
        assert field.value() == before  # clicking and typing do nothing
    dialog.close()
    dialog.deleteLater()
