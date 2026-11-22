"""Pytest configuration and shared fixtures for Lumination."""

import gc
import tempfile

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

# Keep every QSettings() used by tests (saved language, last project) away from
# the user's real settings.
_SETTINGS_DIR = tempfile.mkdtemp(prefix="lumination-test-settings-")
QCoreApplication.setOrganizationName("LuminationTests")
QCoreApplication.setApplicationName("LuminationTests")
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, _SETTINGS_DIR)


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _english_between_tests():
    """Each test starts and ends in English so a language switch cannot leak."""
    from i18n.translations import TranslationManager

    TranslationManager.get_instance().set_language("en", persist=False)
    QSettings().remove("new_survey_defaults")  # remembered setup choices must not leak between tests
    yield
    TranslationManager.get_instance().set_language("en", persist=False)
    # Collect each test's leftover Qt wrappers right away, at a known-safe moment. Left to run at a
    # random point later, Python 3.14's collector occasionally crashes inside PySide6.
    gc.collect()
