"""Modern Engineering Stylesheet and Visual Theme for PySide6.

Designed with clean typography, balanced contrast, and subtle border radius.
Avoids cliché tropes (no dark purple gradients, no cluttered bento boxes).
"""

MAIN_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
}

/* ToolBar */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
    spacing: 6px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 8px;
    font-weight: 500;
    color: #334155;
}

QToolButton:hover {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #0f172a;
}

QToolButton:pressed {
    background-color: #e2e8f0;
}

/* Menu Bar */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    color: #1e293b;
    font-size: 12px;
    padding: 2px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #f1f5f9;
    color: #0f172a;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px;
    color: #1e293b;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}

QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 2px;
}

/* Dock Widgets */
QDockWidget {
    font-weight: 600;
    color: #0f172a;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}

QDockWidget::title {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #334155;
}

/* GroupBox and Cards */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 18px;
    font-weight: 600;
    color: #1e3a8a;
    padding: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    background-color: #ffffff;
    border-radius: 3px;
    left: 10px;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    color: #334155;
}

QPushButton:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton:pressed {
    background-color: #f1f5f9;
}

QPushButton:disabled {
    background-color: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
}

QPushButton.primary {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    color: #ffffff;
    font-weight: 600;
}

QPushButton.primary:hover {
    background-color: #1d4ed8;
    border-color: #1e40af;
}

QPushButton.primary:pressed {
    background-color: #1e40af;
}

QPushButton.danger {
    background-color: #ef4444;
    border: 1px solid #dc2626;
    color: #ffffff;
}

QPushButton.danger:hover {
    background-color: #dc2626;
}

/* Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 5px 8px;
    color: #0f172a;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1.5px solid #2563eb;
}

/* Tables */
QTableView, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1d4ed8;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: 600;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #cbd5e1;
    border-right: 1px solid #f1f5f9;
}

QHeaderView::section:horizontal {
    border-bottom: 1px solid #cbd5e1;
}

/* Checkboxes and Radio buttons */
QCheckBox, QRadioButton {
    spacing: 6px;
    color: #334155;
    font-weight: 500;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #1d4ed8;
}

/* Radio buttons are round and filled when selected (they used to look unselected). */
QRadioButton::indicator {
    border-radius: 8px;
}

QRadioButton::indicator:checked {
    background-color: #2563eb;
    border: 4px solid #dbeafe;
}

QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {
    background-color: #f1f5f9;
    border-color: #e2e8f0;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    color: #475569;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1e3a8a;
    font-weight: 600;
    border-bottom: 2px solid #2563eb;
}

/* Status Bar */
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
    color: #475569;
    font-size: 11px;
    padding: 2px 6px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
