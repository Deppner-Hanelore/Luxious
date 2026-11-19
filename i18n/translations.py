"""Multi-Language Localization Engine for Lumination.

Supports English (default), Romanian (Română), and German (Deutsch).
Provides dynamic runtime language switching across all UI strings.
"""

from __future__ import annotations
from typing import Dict, Any, Callable, List
from PySide6.QtCore import QObject, Signal


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Menus
        "menu_file": "File",
        "menu_new_project": "New Project...",
        "menu_open_project": "Open Project...",
        "menu_save_project": "Save Project",
        "menu_save_project_as": "Save Project As...",
        "menu_exit": "Exit",
        "menu_csv_export": "CSV & Export",
        "menu_import_csv": "Import Measurements from CSV...",
        "menu_export_csv": "Export Measurements to CSV...",
        "menu_export_pdf": "Export PDF Survey Report...",
        "menu_export_image": "Export High-Resolution Map Image...",
        "menu_edit": "Edit",
        "menu_undo": "Undo",
        "menu_redo": "Redo",
        "menu_delete_point": "Delete Selected Point",
        "menu_view": "View",
        "menu_toggle_sidebar": "Toggle Sidebar",
        "menu_language": "Language",
        "menu_help": "Help",
        "menu_about": "About Lumination",
        "menu_shortcuts": "Keyboard Shortcuts",
        "menu_methodology": "Measurement Methodology",

        # Toolbar & Actions
        "action_new": "New",
        "action_open": "Open",
        "action_save": "Save",
        "action_undo": "Undo",
        "action_redo": "Redo",
        "action_regen_grid": "Grid Setup",
        "action_add_custom": "Add Custom Point",
        "action_exit_add_mode": "Done Adding",
        "action_delete_point": "Delete Point",
        "action_sidebar": "Sidebar",
        "action_zoom_in": "Zoom In",
        "action_zoom_out": "Zoom Out",
        "action_reset_view": "Reset View",

        # Survey Mode Bar
        "survey_point": "Point:",
        "survey_reading": "Reading:",
        "survey_save_next": "Save & Next",
        "survey_prev": "Prev",
        "survey_next": "Next",
        "survey_next_unmeasured": "Next Unmeasured",
        "survey_progress": "Survey Progress:",
        "survey_completed": "completed",
        "survey_possible_outlier": "Possible outlier:",
        "survey_record_next": "Record & next",
        "survey_skip_point": "Skip point",
        "survey_pending": "Pending",
        "survey_recorded": "Recorded",
        "survey_select_point": "Select measurement point",
        "survey_complete": "Survey complete · all points recorded",

        # Canvas & Map
        "canvas_x_axis": "X (meters)",
        "canvas_y_axis": "Y (meters)",
        "canvas_tooltip_point": "Point",
        "canvas_tooltip_lux": "Lux",
        "canvas_tooltip_pos": "Position",
        "canvas_tooltip_interp": "Interpolated",
        "canvas_collinear_warning": "A 2D illuminance field cannot be reconstructed from the current measurement geometry. Add measurements at non-collinear positions.",
        "canvas_placement_hint": "Click inside room to place new sensor. Snap assist aligns with room center and symmetric points.",
        "canvas_min_tag": "Min",
        "canvas_max_tag": "Max",

        # Table & Panels
        "tab_measurements": "Measurements Table",
        "tab_kpis": "Photometric KPIs",
        "tab_target": "Target Comparison",
        "tab_simulated": "Simulated vs Measured",
        "tab_layers": "Layers & Settings",

        # Table Columns
        "col_point_id": "Point ID",
        "col_x": "X (m)",
        "col_y": "Y (m)",
        "col_lux": "Measured (lx)",
        "col_expected": "Expected (lx)",
        "col_delta": "Delta (lx)",
        "col_device": "Instrument",
        "col_time": "Timestamp",
        "col_notes": "Notes",

        # KPI Panel
        "kpi_summary": "Photometric Summary",
        "kpi_e_avg": "Average Illuminance (Eavg)",
        "kpi_e_min": "Minimum Illuminance (Emin)",
        "kpi_e_max": "Maximum Illuminance (Emax)",
        "kpi_u0": "Uniformity U0 (Emin/Eavg)",
        "kpi_u1": "Uniformity U1 (Emin/Emax)",
        "kpi_std_dev": "Standard Deviation (σ)",
        "kpi_median": "Median Illuminance",
        "kpi_range": "Range (Emax - Emin)",
        "kpi_points_count": "Measurement Points",

        # Target Panel
        "target_panel_title": "Comparison with Selected Target Illuminance",
        "target_input_label": "Target (lx):",
        "target_progress_label": "Points Meeting Target:",
        "target_avg_measured": "Avg Measured:",
        "target_below": "Below Target:",
        "target_above": "≥ Target:",
        "target_max_deficit": "Max Deficit:",
        "target_max_surplus": "Max Surplus:",
        "target_mean_abs_dev": "Mean Abs Deviation:",
        "target_mean_dev": "Mean Deviation:",

        # Dialogs
        "dlg_new_project_title": "Create New Room Survey",
        "dlg_room_name": "Room / Project Name:",
        "dlg_room_length": "Room Length X (m):",
        "dlg_room_width": "Room Width Y (m):",
        "dlg_room_height": "Ceiling Height (m):",
        "dlg_plane_height": "Working Plane Height (m):",
        "dlg_target_lux": "Target Illuminance (lx):",
        "dlg_grid_mode": "Grid Definition Mode:",
        "dlg_grid_by_count": "By Number of Rows and Columns",
        "dlg_grid_by_spacing": "By Distance Between Points in Meters",
        "dlg_spacing_x": "Spacing X (m):",
        "dlg_spacing_y": "Spacing Y (m):",
        "dlg_traversal_order": "Survey Walking Traversal Order:",
        "dlg_traversal_serpentine": "Serpentine / Snake Pattern (L→R, R→L)",
        "dlg_traversal_left_to_right": "Standard Row-by-Row (Left to Right)",
        "dlg_wall_margin": "Wall Margin Band (m):",
        "dlg_cancel": "Cancel",
        "dlg_ok": "OK",
        "dlg_apply": "Apply",
    },

    "ro": {
        # Meniuri
        "menu_file": "Fișier",
        "menu_new_project": "Proiect nou...",
        "menu_open_project": "Deschide proiect...",
        "menu_save_project": "Salvează proiect",
        "menu_save_project_as": "Salvează proiect ca...",
        "menu_exit": "Ieșire",
        "menu_csv_export": "CSV și Export",
        "menu_import_csv": "Importă măsurători din CSV...",
        "menu_export_csv": "Exportă măsurători în CSV...",
        "menu_export_pdf": "Exportă raport PDF...",
        "menu_export_image": "Exportă imagine de înaltă rezoluție...",
        "menu_edit": "Editare",
        "menu_undo": "Anulează (Undo)",
        "menu_redo": "Refă (Redo)",
        "menu_delete_point": "Șterge punctul selectat",
        "menu_view": "Vizualizare",
        "menu_toggle_sidebar": "Comută panou lateral",
        "menu_language": "Limbă",
        "menu_help": "Ajutor",
        "menu_about": "Despre Lumination",
        "menu_shortcuts": "Scurtături tastatură",
        "menu_methodology": "Metodologie măsurători",

        # Toolbar & Actions
        "action_new": "Nou",
        "action_open": "Deschide",
        "action_save": "Salvează",
        "action_undo": "Anulează",
        "action_redo": "Refă",
        "action_regen_grid": "Configurare grilă",
        "action_add_custom": "Adaugă punct personalizat",
        "action_exit_add_mode": "Finalizare adăugare",
        "action_delete_point": "Șterge punct",
        "action_sidebar": "Panou lateral",
        "action_zoom_in": "Mărește",
        "action_zoom_out": "Micșorează",
        "action_reset_view": "Resetează vizualizarea",

        # Survey Mode Bar
        "survey_point": "Punct:",
        "survey_reading": "Citire:",
        "survey_save_next": "Salvează și Următorul",
        "survey_prev": "Anterior",
        "survey_next": "Următor",
        "survey_next_unmeasured": "Următorul nemăsurat",
        "survey_progress": "Progres măsurători:",
        "survey_completed": "finalizat",
        "survey_possible_outlier": "Posibilă valoare aberantă:",
        "survey_record_next": "Înregistrează și continuă",
        "survey_skip_point": "Omite punctul",
        "survey_pending": "În așteptare",
        "survey_recorded": "Înregistrat",
        "survey_select_point": "Selectați punctul de măsurare",
        "survey_complete": "Măsurătoare completă · toate punctele sunt înregistrate",

        # Canvas & Map
        "canvas_x_axis": "X (metri)",
        "canvas_y_axis": "Y (metri)",
        "canvas_tooltip_point": "Punct",
        "canvas_tooltip_lux": "Lux",
        "canvas_tooltip_pos": "Poziție",
        "canvas_tooltip_interp": "Interpolat",
        "canvas_collinear_warning": "Câmpul de iluminare 2D nu poate fi reconstruit din geometria actuală. Adăugați măsurători în poziții necoliniare.",
        "canvas_placement_hint": "Faceți clic în cameră pentru a plasa un nou senzor. Ghidajul aliniază cu centrul și punctele simetrice.",
        "canvas_min_tag": "Min",
        "canvas_max_tag": "Max",

        # Table & Panels
        "tab_measurements": "Tabel măsurători",
        "tab_kpis": "Indicatori fotometrici",
        "tab_target": "Comparație cu valoarea țintă",
        "tab_simulated": "Simulat vs Măsurat",
        "tab_layers": "Straturi și Setări",

        # Table Columns
        "col_point_id": "ID Punct",
        "col_x": "X (m)",
        "col_y": "Y (m)",
        "col_lux": "Măsurat (lx)",
        "col_expected": "Așteptat (lx)",
        "col_delta": "Diferență (lx)",
        "col_device": "Instrument",
        "col_time": "Data/Ora",
        "col_notes": "Observații",

        # KPI Panel
        "kpi_summary": "Rezumat fotometric",
        "kpi_e_avg": "Iluminare medie (Emed)",
        "kpi_e_min": "Iluminare minimă (Emin)",
        "kpi_e_max": "Iluminare maximă (Emax)",
        "kpi_u0": "Uniformitate U0 (Emin/Emed)",
        "kpi_u1": "Uniformitate U1 (Emin/Emax)",
        "kpi_std_dev": "Deviație standard (σ)",
        "kpi_median": "Iluminare mediană",
        "kpi_range": "Interval (Emax - Emin)",
        "kpi_points_count": "Puncte de măsurare",

        # Target Panel
        "target_panel_title": "Comparație cu iluminarea țintă selectată",
        "target_input_label": "Țintă (lx):",
        "target_progress_label": "Puncte care ating ținta:",
        "target_avg_measured": "Medie măsurată:",
        "target_below": "Sub țintă:",
        "target_above": "≥ Țintă:",
        "target_max_deficit": "Deficit maxim:",
        "target_max_surplus": "Surplus maxim:",
        "target_mean_abs_dev": "Deviație medie absolută:",
        "target_mean_dev": "Deviație medie:",

        # Dialogs
        "dlg_new_project_title": "Creare proiect nou de măsurători",
        "dlg_room_name": "Nume cameră / proiect:",
        "dlg_room_length": "Lungime cameră X (m):",
        "dlg_room_width": "Lățime cameră Y (m):",
        "dlg_room_height": "Înălțime tavan (m):",
        "dlg_plane_height": "Înălțime plan de lucru (m):",
        "dlg_target_lux": "Iluminare țintă (lx):",
        "dlg_grid_mode": "Mod definire grilă:",
        "dlg_grid_by_count": "După număr de rânduri și coloane",
        "dlg_grid_by_spacing": "După distanța dintre puncte în metri",
        "dlg_spacing_x": "Distanță X (m):",
        "dlg_spacing_y": "Distanță Y (m):",
        "dlg_traversal_order": "Traseu de parcurgere la măsurare:",
        "dlg_traversal_serpentine": "Model șerpuit / serpentină (S→D, D→S)",
        "dlg_traversal_left_to_right": "Standard rând cu rând (Stânga la Dreapta)",
        "dlg_wall_margin": "Bandă margine perete (m):",
        "dlg_cancel": "Anulare",
        "dlg_ok": "OK",
        "dlg_apply": "Aplică",
    },

    "de": {
        # Menüs
        "menu_file": "Datei",
        "menu_new_project": "Neues Projekt...",
        "menu_open_project": "Projekt öffnen...",
        "menu_save_project": "Projekt speichern",
        "menu_save_project_as": "Projekt speichern unter...",
        "menu_exit": "Beenden",
        "menu_csv_export": "CSV & Export",
        "menu_import_csv": "Messungen aus CSV importieren...",
        "menu_export_csv": "Messungen in CSV exportieren...",
        "menu_export_pdf": "PDF-Messbericht exportieren...",
        "menu_export_image": "Hochauflösendes Kartenbild exportieren...",
        "menu_edit": "Bearbeiten",
        "menu_undo": "Rückgängig (Undo)",
        "menu_redo": "Wiederholen (Redo)",
        "menu_delete_point": "Ausgewählten Punkt löschen",
        "menu_view": "Ansicht",
        "menu_toggle_sidebar": "Seitenleiste umschalten",
        "menu_language": "Sprache",
        "menu_help": "Hilfe",
        "menu_about": "Über Lumination",
        "menu_shortcuts": "Tastenkürzel",
        "menu_methodology": "Messmethodik",

        # Toolbar & Actions
        "action_new": "Neu",
        "action_open": "Öffnen",
        "action_save": "Speichern",
        "action_undo": "Rückgängig",
        "action_redo": "Wiederholen",
        "action_regen_grid": "Raster einrichten",
        "action_add_custom": "Eigenen Punkt hinzufügen",
        "action_exit_add_mode": "Hinzufügen beenden",
        "action_delete_point": "Punkt löschen",
        "action_sidebar": "Seitenleiste",
        "action_zoom_in": "Vergrößern",
        "action_zoom_out": "Verkleinern",
        "action_reset_view": "Ansicht zurücksetzen",

        # Survey Mode Bar
        "survey_point": "Punkt:",
        "survey_reading": "Messwert:",
        "survey_save_next": "Speichern & Weiter",
        "survey_prev": "Zurück",
        "survey_next": "Vor",
        "survey_next_unmeasured": "Nächster ungemessener",
        "survey_progress": "Messfortschritt:",
        "survey_completed": "abgeschlossen",
        "survey_possible_outlier": "Möglicher Ausreißer:",
        "survey_record_next": "Aufzeichnen & weiter",
        "survey_skip_point": "Punkt überspringen",
        "survey_pending": "Ausstehend",
        "survey_recorded": "Erfasst",
        "survey_select_point": "Messpunkt auswählen",
        "survey_complete": "Messung abgeschlossen · alle Punkte erfasst",

        # Canvas & Map
        "canvas_x_axis": "X (Meter)",
        "canvas_y_axis": "Y (Meter)",
        "canvas_tooltip_point": "Punkt",
        "canvas_tooltip_lux": "Lux",
        "canvas_tooltip_pos": "Position",
        "canvas_tooltip_interp": "Interpoliert",
        "canvas_collinear_warning": "Aus der aktuellen Messgeometrie kann kein 2D-Beleuchtungsstärkefeld rekonstruiert werden. Fügen Sie Messungen an nicht-kollinearen Positionen hinzu.",
        "canvas_placement_hint": "Klicken Sie in den Raum, um einen neuen Sensor zu platzieren. Die Fangfunktion richtet sich an der Raummitte und symmetrischen Punkten aus.",
        "canvas_min_tag": "Min",
        "canvas_max_tag": "Max",

        # Table & Panels
        "tab_measurements": "Messtabelle",
        "tab_kpis": "Photometrische Kennzahlen",
        "tab_target": "Sollwert-Vergleich",
        "tab_simulated": "Simulation vs Messung",
        "tab_layers": "Ebenen & Einstellungen",

        # Table Columns
        "col_point_id": "Punkt-ID",
        "col_x": "X (m)",
        "col_y": "Y (m)",
        "col_lux": "Gemessen (lx)",
        "col_expected": "Erwartet (lx)",
        "col_delta": "Differenz (lx)",
        "col_device": "Messgerät",
        "col_time": "Zeitstempel",
        "col_notes": "Notizen",

        # KPI Panel
        "kpi_summary": "Photometrische Zusammenfassung",
        "kpi_e_avg": "Mittlere Beleuchtungsstärke (E_mittel)",
        "kpi_e_min": "Minimale Beleuchtungsstärke (E_min)",
        "kpi_e_max": "Maximale Beleuchtungsstärke (E_max)",
        "kpi_u0": "Gleichmäßigkeit U0 (E_min/E_mittel)",
        "kpi_u1": "Gleichmäßigkeit U1 (E_min/E_max)",
        "kpi_std_dev": "Standardabweichung (σ)",
        "kpi_median": "Median-Beleuchtungsstärke",
        "kpi_range": "Spannweite (E_max - E_min)",
        "kpi_points_count": "Messpunkte",

        # Target Panel
        "target_panel_title": "Vergleich mit gewähltem Sollwert",
        "target_input_label": "Sollwert (lx):",
        "target_progress_label": "Punkte, die den Sollwert erfüllen:",
        "target_avg_measured": "Durchschnitt gemessen:",
        "target_below": "Unter Sollwert:",
        "target_above": "≥ Sollwert:",
        "target_max_deficit": "Maximales Defizit:",
        "target_max_surplus": "Maximaler Überschuss:",
        "target_mean_abs_dev": "Mittlere absolute Abweichung:",
        "target_mean_dev": "Mittlere Abweichung:",

        # Dialogs
        "dlg_new_project_title": "Neues Raum-Messprojekt erstellen",
        "dlg_room_name": "Raum- / Projektname:",
        "dlg_room_length": "Raumlänge X (m):",
        "dlg_room_width": "Raumbreite Y (m):",
        "dlg_room_height": "Deckenhöhe (m):",
        "dlg_plane_height": "Nutzebenenhöhe (m):",
        "dlg_target_lux": "Soll-Beleuchtungsstärke (lx):",
        "dlg_grid_mode": "Raster-Definitionsmodus:",
        "dlg_grid_by_count": "Nach Anzahl von Zeilen und Spalten",
        "dlg_grid_by_spacing": "Nach Punktabstand in Metern",
        "dlg_spacing_x": "Abstand X (m):",
        "dlg_spacing_y": "Abstand Y (m):",
        "dlg_traversal_order": "Messpfad-Reihenfolge:",
        "dlg_traversal_serpentine": "Mäander- / Schlangenmuster (L→R, R→L)",
        "dlg_traversal_left_to_right": "Standard zeilenweise (Links nach Rechts)",
        "dlg_wall_margin": "Wandabstand (m):",
        "dlg_cancel": "Abbrechen",
        "dlg_ok": "OK",
        "dlg_apply": "Übernehmen",
    },
}


class TranslationManager(QObject):
    """Singleton Translation Manager emitting language_changed signals."""
    language_changed = Signal(str)

    _instance: Optional[TranslationManager] = None

    def __init__(self) -> None:
        super().__init__()
        self.current_language: str = "en"

    @classmethod
    def get_instance(cls) -> TranslationManager:
        if cls._instance is None:
            cls._instance = TranslationManager()
        return cls._instance

    def set_language(self, lang_code: str) -> None:
        """Switch current language ('en', 'ro', 'de')."""
        if lang_code in TRANSLATIONS and lang_code != self.current_language:
            self.current_language = lang_code
            self.language_changed.emit(lang_code)

    def tr(self, key: str) -> str:
        """Translate a key into the active language, falling back to English or the key itself."""
        lang_dict = TRANSLATIONS.get(self.current_language, TRANSLATIONS["en"])
        if key in lang_dict:
            return lang_dict[key]
        return TRANSLATIONS["en"].get(key, key)


def tr(key: str) -> str:
    """Global helper function to translate strings."""
    return TranslationManager.get_instance().tr(key)
