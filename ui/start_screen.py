"""Offline start screen for creating, opening, resuming, or practicing a survey."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal

from i18n.translations import tr, TranslationManager
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StartScreenWidget(QWidget):
    """Present the first useful action without loading sample readings by default."""

    new_survey_requested = Signal()
    open_survey_requested = Signal()
    resume_requested = Signal()
    practice_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("startScreen")
        self.setMinimumSize(520, 360)

        content = QFrame(self)
        content.setObjectName("startCard")
        content.setFixedWidth(600)

        title = QLabel(tr("start_title"), content)
        title.setObjectName("startTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        self.lbl_title = title

        self.lbl_resume_title = QLabel("", content)
        self.lbl_resume_title.setObjectName("resumeTitle")
        self.lbl_resume_detail = QLabel("", content)
        self.lbl_resume_detail.setWordWrap(True)
        self.lbl_resume_detail.setObjectName("resumeDetail")

        self.btn_resume = QPushButton(tr("start_resume"), content)
        self.btn_resume.setObjectName("primaryStartAction")
        self.btn_resume.setMinimumHeight(52)
        self.btn_resume.clicked.connect(self.resume_requested.emit)

        self.btn_new = QPushButton(tr("start_new"), content)
        self.btn_new.setObjectName("primaryStartAction")
        self.btn_new.setMinimumHeight(52)
        self.btn_new.clicked.connect(self.new_survey_requested.emit)

        self.btn_open = QPushButton(tr("start_open"), content)
        self.btn_open.setMinimumHeight(48)
        self.btn_open.clicked.connect(self.open_survey_requested.emit)

        self.btn_practice = QPushButton(tr("start_practice"), content)
        self.btn_practice.setMinimumHeight(44)
        self.btn_practice.clicked.connect(self.practice_requested.emit)

        card_layout = QVBoxLayout(content)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(12)
        card_layout.addWidget(title)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.lbl_resume_title)
        card_layout.addWidget(self.lbl_resume_detail)
        card_layout.addWidget(self.btn_resume)
        card_layout.addWidget(self.btn_new)
        card_layout.addWidget(self.btn_open)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.btn_practice)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch()
        outer.addWidget(content, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        self.setStyleSheet(
            """
            QWidget#startScreen { background: #f4f6f8; }
            QFrame#startCard {
                background: #ffffff;
                border: 1px solid #c5cdd7;
                border-radius: 8px;
            }
            QLabel#startTitle { color: #17212b; font-size: 18pt; font-weight: 600; }
            QLabel#resumeTitle { color: #17212b; font-size: 12pt; font-weight: 600; }
            QLabel#resumeDetail, QLabel#startHint { color: #52606d; font-size: 11pt; }
            QPushButton {
                color: #17212b;
                background: #ffffff;
                border: 1px solid #9aa6b2;
                border-radius: 6px;
                padding: 8px 14px;
                text-align: left;
            }
            QPushButton:hover { background: #eef3f8; }
            QPushButton:focus { border: 2px solid #1d4ed8; }
            QPushButton#primaryStartAction {
                color: #ffffff;
                background: #1d4ed8;
                border-color: #1d4ed8;
                font-size: 12pt;
                font-weight: 600;
            }
            QPushButton#primaryStartAction:hover { background: #1e40af; }
            QPushButton:disabled { color: #52606d; background: #f4f6f8; }
            """
        )

        self.show_resume(None, None)
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, *_args) -> None:
        self.lbl_title.setText(tr("start_title"))
        self.btn_resume.setText(tr("start_resume"))
        self.btn_new.setText(tr("start_new"))
        self.btn_open.setText(tr("start_open"))
        self.btn_practice.setText(tr("start_practice"))

    def show_resume(self, title: Optional[str], detail: Optional[str]) -> None:
        """Show a resume action only when a usable project or recovery exists."""
        available = bool(title and detail)
        self.lbl_resume_title.setText(title or "")
        self.lbl_resume_detail.setText(detail or "")
        self.lbl_resume_title.setVisible(available)
        self.lbl_resume_detail.setVisible(available)
        self.btn_resume.setVisible(available)
