"""The graph alone in its own large window (about 80% of the screen).

It holds a second map canvas with the same tools; clicking points and typing
readings work exactly as on the main map. The main window keeps both in sync.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from i18n.translations import TranslationManager, tr
from ui.room_canvas import RoomCanvasWidget
from utils.app_info import APP_NAME

SCREEN_FRACTION = 0.8


class GraphWindow(QWidget):
    """A separate top-level window showing only the map."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.canvas_widget = RoomCanvasWidget(self, show_fullscreen_button=False, show_colorbar=False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.canvas_widget)
        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(tr("graph_window_title", app=APP_NAME))

    def show_large(self) -> None:
        """Open covering about 80% of the screen the main window is on, centred."""
        anchor = self.parentWidget()
        screen = anchor.screen() if anchor is not None else self.screen()
        area = screen.availableGeometry()
        width = int(area.width() * SCREEN_FRACTION)
        height = int(area.height() * SCREEN_FRACTION)
        self.resize(width, height)
        self.move(area.x() + (area.width() - width) // 2, area.y() + (area.height() - height) // 2)
        self.show()
        self.raise_()
        self.activateWindow()
        self.canvas_widget.reset_view()
