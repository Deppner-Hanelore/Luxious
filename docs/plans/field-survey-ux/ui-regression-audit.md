# Field UI regression audit

Date: 13 October 2026. Scope: the uncommitted field-survey UI implementation, compared with existing project features. This is regression evidence for the current workspace, not release or accessibility certification.

## Findings and fixes

| Finding | Fix and verification |
| --- | --- |
| Review/Edit docks squeezed the survey bar until action labels were clipped at 960×600 | Survey controls now occupy a full-width native toolbar. Review hides capture controls. Small windows show one detail dock at a time; panels scroll when their content is larger than the dock. Button geometry was checked in EN/RO/DE at three window sizes. |
| Language changes recreated actions without retiring old shortcuts and restoring mode permissions | Old shortcuts are cleared before actions are retired. New menu actions receive the current permissions. Repeated language switching leaves one active Save shortcut and keeps Review mutations disabled. |
| Done editing left the Survey docks open; map selection redraws reset zoom | Done restores the originating workspace, selection, focus, and Survey dock layout. Canvas redraws preserve the current view for the same project/room. New geometry resets the view. |
| Empty projects retained an old survey point/input and offered dead navigation | Empty bindings clear the point and field; Record, Previous, Skip, and Next pending are disabled. |
| Skip at the last point did nothing even when earlier skipped points remained | Skip finds the next pending point, including earlier skipped work, without writing a measurement. Navigation controls disable when they have no destination. |
| Meter-to-MainWindow capture accessed a missing sample profile field | Samples carry the selected profile ID. The end-to-end callback records provenance and rejects repeated sample delivery. This check uses a synthetic qualified test profile; it does not qualify real hardware. |
| The device banner clipped the Capture button and connection state | The monitor now has a value/action row and a wrapping status row. Empty USB/Bluetooth selections disable Connect; capture remains disabled for unsupported profiles. |
| Recorded readings could be rounded when re-entered through the survey bar, table, popup, or notes-only point dialog | Edit values retain full float precision. Unchanged point-dialog controls preserve coordinates, reading timestamps, and provenance. Locale-aware entry accepts German decimal commas. |
| Saved Review projects and recovery during Edit could resume into Survey | Named saves and recovery retain the prior stable Survey/Review workspace. Direct project binding respects saved Review context. |
| Review offered an editable map popup despite rejecting the write | Map selection remains available, but reading popups appear only for allowed Survey/Edit operations. Blank map clicks preserve the central selection. |
| New setup omitted the existing optional surveyor name and spacing-based initial grid | Both options are restored within the three-step flow; manual count-based setup remains the default. Invalid plane/margin geometry is explained before advancing. |
| Expected/difference maps could reuse measured values; negative differences could fail or be dropped | Display reconstruction receives the selected expected or signed difference field. Signed reconstruction is explicit and confined to transient display data; physical readings remain unchanged. This was a pre-existing numerical/display problem found during the audit. |
| An unsupported CSS cursor property flooded native launch logs; shortcut help still advertised Ctrl+X as Redo | Clickable KPI cards now use Qt's native cursor API. Help reports the actual configured Redo shortcut and mode-scoped entry/deletion behavior. |

## Verification

- Full suite: **83 passed**. Added 28 regression checks in `tests/test_ui_regressions.py`.
- Actual QPushButton clicks and QAction triggers exercised recording, correction, Skip, point addition/deletion, clear, undo/redo, grid changes, New/Save/Open, and CSV/PDF/image export file creation. File dialogs and confirmation prompts were supplied with test answers.
- Checks cover empty projects, original precision/provenance, locale changes, decimal entry, unique shortcuts, mode gating, saved/recovered workspace, point/focus/zoom return state, repeated device sample delivery, expected maps, and signed difference maps.
- Native offscreen layout checks: EN/RO/DE at 960×600, 1380×860, and 1920×1080 logical pixels; an additional run at Qt scale factor 2. Screenshots were inspected for the minimum-size workspaces, default Review, large Edit, and setup/device dialogs. Native offscreen evidence is not a Windows screen-reader or field-touch trial.
- Dialog checks cover setup, grid generation, point details, device connection, CSV preview, and export; no undersized action-button text bounds remained in the checked layouts.

## Remaining verification boundaries

Physical meters still need T12 qualification. Some new setup/device text remains English and the full accessibility/enlarged-text audit remains T11. Narrow translated analysis panels can require horizontal or vertical scrolling. Large-grid latency, field usability, complete export semantics, and clean-machine Windows evidence remain the corresponding planned T09–T14 work.

The desktop window opened before this audit continues using the previous in-memory code until restarted. Audit runs did not close or replace that window or its working survey.
