# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for the Luxious desktop application.

Packages all core and lazy-loaded modules (PySide6, NumPy, SciPy, Matplotlib, ReportLab)
into a standalone Windows desktop executable with zero console window.
"""

import os

project_dir = os.path.abspath(SPECPATH)

hidden_imports = [
    # Core PySide6
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    
    # NumPy & Scientific stack
    'numpy',
    
    # SciPy (lazy-loaded modules)
    'scipy',
    'scipy.interpolate',
    'scipy.spatial',
    'scipy.spatial.distance',
    'scipy.ndimage',
    'scipy.special',
    
    # Matplotlib
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_agg',
    'matplotlib.figure',
    'matplotlib.ticker',
    'matplotlib.patches',
    'matplotlib.path',
    'matplotlib.colors',
    'matplotlib.cm',
    'matplotlib.colorbar',
    
    # ReportLab (lazy-loaded PDF engine)
    'reportlab',
    'reportlab.platypus',
    'reportlab.platypus.flowables',
    'reportlab.platypus.paragraph',
    'reportlab.platypus.tables',
    'reportlab.platypus.doctemplate',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.colors',
    'reportlab.lib.styles',
    'reportlab.lib.units',
    'reportlab.pdfgen.canvas',
    
    # Application packages
    'models.measurement',
    'models.room',
    'models.project',
    'analysis.statistics',
    'analysis.interpolation',
    'analysis.contours',
    'analysis.comparison',
    'analysis.outliers',
    'visualization.map_plotter',
    'visualization.chart_plotter',
    'visualization.color_maps',
    'persistence.project_io',
    'persistence.csv_io',
    'persistence.table_io',
    'persistence.recovery',
    'reporting.pdf_report',
    'reporting.chart_exporter',
    'ui.styles',
    'ui.main_window',
    'ui.room_canvas',
    'ui.graph_window',
    'ui.survey_mode_widget',
    'ui.start_screen',
    'ui.workflow_controller',
    'ui.measurement_table',
    'ui.results_panel',
    'ui.target_panel',
    'ui.comparison_panel',
    'ui.layer_control_widget',
    'ui.dialogs.new_project_dialog',
    'ui.dialogs.grid_generator_dialog',
    'ui.dialogs.point_edit_dialog',
    'ui.dialogs.export_dialog',
    'ui.dialogs.survey_setup_dialog',
    'ui.dialogs.import_preview_dialog',
    'ui.dialogs.table_setup_dialog',
    'openpyxl',
    'i18n.translations',
    'i18n.strings',
    'utils.undo_commands',
    'utils.build_smoke',
    'utils.app_info',
    'ui.icons',
]

a = Analysis(
    [os.path.join(project_dir, 'main.py')],
    pathex=[project_dir],
    binaries=[],
    datas=[(os.path.join(project_dir, 'assets', 'luxious.ico'), 'assets')],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pandas', 'IPython', 'jupyter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Luxious',
    icon=os.path.join(project_dir, 'assets', 'luxious.ico'),  # app icon (from Luxious.ico)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # No command prompt window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Luxious',
)
