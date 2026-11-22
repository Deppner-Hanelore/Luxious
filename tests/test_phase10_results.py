"""Phase 10: on the results cards only the minimum and maximum values are clickable."""

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from analysis.statistics import calculate_statistics
from models.project import LuminationProject
from models.room import Room
from ui.results_panel import ResultsPanel


def _click(widget):
    for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        event = QMouseEvent(kind, QPointF(3, 3), QPointF(3, 3), Qt.MouseButton.LeftButton,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, event)


def _panel():
    project = LuminationProject(name="R", room=Room(length=6.0, width=4.0))
    project.regenerate_grid(rows=2, cols=2)
    for value, point in zip((300, 450, 500, 620), project.points):
        point.record_reading(value)
    panel = ResultsPanel()
    panel.update_statistics(calculate_statistics(project.points))
    panel.show()
    QApplication.processEvents()
    return panel, project


def test_only_min_and_max_values_select_a_point(qapp):
    panel, project = _panel()
    picked = []
    panel.highlight_point_requested.connect(picked.append)
    _click(panel.card_min.lbl_value)
    _click(panel.card_max.lbl_value)
    assert picked == [project.points[0].id, project.points[3].id]
    # Title, subtitle and the rest of the card do nothing; neither do the other cards.
    for widget in (panel.card_min.lbl_title, panel.card_min.lbl_sub, panel.card_min,
                   panel.card_u0, panel.card_u0.lbl_value, panel.card_std.lbl_value,
                   panel.card_med.lbl_value, panel.card_range.lbl_value, panel.card_avg.lbl_value):
        _click(widget)
    assert len(picked) == 2
    panel.close()


def test_nothing_else_looks_selectable(qapp):
    panel, _project = _panel()
    clickable = [card.lbl_value for card in (panel.card_min, panel.card_max)]
    for card in (panel.card_avg, panel.card_u0, panel.card_min, panel.card_max,
                 panel.card_u1, panel.card_std, panel.card_med, panel.card_range):
        assert "hover" not in card.styleSheet().split("kpiValueLink:hover")[0]
        assert card.cursor().shape() == Qt.CursorShape.ArrowCursor
        for label in (card.lbl_title, card.lbl_sub):
            assert label.cursor().shape() == Qt.CursorShape.ArrowCursor
        if card.lbl_value in clickable:
            assert card.lbl_value.cursor().shape() == Qt.CursorShape.PointingHandCursor
            assert card.lbl_value.objectName() == "kpiValueLink"
        else:
            assert card.lbl_value.cursor().shape() == Qt.CursorShape.ArrowCursor
            assert card.lbl_value.objectName() == "kpiValue"
    panel.close()
