"""Phase 11: Help > Keyboard shortcuts matches the app, is translated and lists no removed features."""

import re

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMessageBox

from i18n.translations import TranslationManager
from models.project import LuminationProject
from models.room import Room


def _shortcuts_text(tmp_path, monkeypatch, lang):
    from persistence.recovery import RecoveryStore
    from ui.main_window import MainWindow

    project = LuminationProject(name="Help", room=Room())
    project.regenerate_grid(rows=2, cols=2)
    window = MainWindow(project, recovery_store=RecoveryStore(str(tmp_path / "r.json")),
                        settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    TranslationManager.get_instance().set_language(lang, persist=False)
    shown = {}
    monkeypatch.setattr(QMessageBox, "information", lambda _parent, title, text: shown.update(title=title, text=text))
    window.act_shortcuts.trigger()
    keys = {name: getattr(window, name).shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            for name in ("act_new", "act_open", "act_save", "act_undo", "act_redo")}
    window.project.is_dirty = False
    window.close()
    return shown, keys


@pytest.mark.parametrize("lang", ["en", "ro", "de"])
def test_shortcut_list_shows_the_real_keys_in_the_active_language(qapp, tmp_path, monkeypatch, lang):
    shown, keys = _shortcuts_text(tmp_path, monkeypatch, lang)
    assert shown["title"]
    for key in keys.values():
        assert f"<b>{key}</b>" in shown["text"]
    assert len(re.findall("<li>", shown["text"])) == 10


def test_shortcut_list_mentions_no_removed_feature(qapp, tmp_path, monkeypatch):
    shown, _keys = _shortcuts_text(tmp_path, monkeypatch, "en")
    text = shown["text"].lower()
    for removed in ("edit mode", "bluetooth", "usb", "skip", "prev", "export", "meter", "(+)", "(-)"):
        assert removed not in text
