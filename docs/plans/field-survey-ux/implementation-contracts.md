# Field survey implementation contracts

Status: implementation contract for the current build. T01–T05 and T07 are
implemented; T06 and the T08–T11 review work remain in progress. T12–T14 still
require physical device access and field evidence.

## Workspace transitions and action policy

| Current workspace | Action | Result | Data mutation |
| --- | --- | --- | --- |
| Survey | Select point / Previous / Next / Skip | Stay in Survey; update selection only | No |
| Survey | Record valid manual or eligible device sample | Record exactly once against the point bound at activation; select next pending point, or show completion | Yes, one undoable reading command |
| Survey | Enter Review | Review | No |
| Survey | Enter Edit | Save Survey and selected point as return context; enter Edit | No |
| Review | Select point / Previous / Next | Stay in Review; update selection only | No |
| Review | Enter Survey | Survey | No |
| Review | Enter Edit | Save Review and selected point as return context; enter Edit | No |
| Review | Record, correct, add/delete/move/clear point, change grid, import | Reject or disable; guide user to Edit | No |
| Edit | Record, correct, add/delete/move/clear point, change grid, commit import | Stay in Edit; apply a single undoable command/transaction | Yes |
| Edit | Done | Restore prior Survey or Review and prior selected point if it still exists | No |
| Any | Save / export | Keep current workspace | No project mutation |

The state and permission primitive is `ui/workflow_controller.py`. It owns only
view/workspace state and policy. The project remains the data authority; command
objects remain the path for user changes. A failed or cancelled operation does
not enter undo history. Deleting the selected point clears selection; the UI
chooses a surviving pending point explicitly. The existing SurveyModeWidget is
now connected to this path: blank input remains pending, explicit zero is valid,
and recorded values require Edit mode before correction.

### Recording rules

- `lux is None` means pending; `lux == 0` is a valid measured value.
- Empty, invalid, or negative manual input cannot record. Navigation never
  writes, and moving to a point never fills an empty input with zero.
- A device sample has a unique operation ID, selected source/profile ID, lux
  value, unit, sample monotonic time, and simulated/physical classification.
  Capture eligibility belongs to the selected session and profile; a transport
  being open alone is insufficient.
- Bind the operation ID to the active point when the user activates Record.
  Retried delivery of the same operation ID is ignored; a new operation ID with
  the same numeric lux value is a distinct valid sample. Sample live updates do
  not mutate a project.
- After a successful record, choose the next pending point in traversal order.
  If no point remains pending, return no point and announce completion; never
  wrap and overwrite the first reading. Skip is navigation and leaves the point
  pending.
- A failed retake preserves the existing value. Edit and correction return to
  the saved workspace and point if it still exists.

## Source and capture contract

The selected source is singular: `manual`, `practice:<profile>`, or a supported
physical `device:<profile>`. A device session reports transport state separately
from data readiness and carries the latest sample identity, source/profile,
unit, and monotonic age. Only a fresh, supported lux sample from the selected
physical profile is eligible for a physical capture. Practice values remain
visibly simulated and export provenance is retained. Until a real device profile
is qualified, the physical-source state must not imply usable readings.

## Persistence and resume contract

Named `.luxproj` files retain full project data and legacy 1.0 loading. A future
versioned extension stores only stable resume context: workspace (Survey or
Review; never restore into Edit), selected point ID, and an optional bounded
recent-file record. If the point is absent, restore to the first pending point,
then first point. Do not serialize transport objects, monotonic sample times,
open handles, or auto-reconnect intent. Recovery snapshots are separate from
named project files and restore the last successfully written project revision.
The UI may say “Recorded” after an in-memory command and “Saved locally” only
after an atomic disk write succeeds.

The current project format writes `format_version: 1.1`, keeps compatibility
with legacy 1.0 files, and persists resume/provenance additions while excluding
transient file path and dirty state. Legacy data is upgraded in memory and is
rewritten only on a successful save. Unknown future major versions fail with a
useful message rather than being silently discarded. Recovery remains a
separate local snapshot.

## Source audit and migration map

| Existing path | Delivered enforcement |
| --- | --- |
| `MainWindow._on_hardware_reading_captured` | Selected fresh qualified sample is consumed once, provenance is retained, and next pending point is selected; no completion wrap |
| `MainWindow._on_measurement_recorded` | Checks workflow permission, validates pending/correction semantics, deduplicates operation IDs, and records through an undo command |
| Canvas edit/add/delete signals | User mutations require Edit; detached edits and structural changes commit through undo commands |
| `MeasurementTableModel.setData` | Direct model writes are rejected; Edit requests are committed by MainWindow commands |
| CSV import handler | Parses a detached project, previews the resulting values, leaves state unchanged on cancel, and applies one undoable transaction |
| New/open project handlers | Start screen offers New/Open/Resume/Practice; dirty replacement uses Save/Discard/Cancel; recent missing paths offer Locate |
| `SurveyModeWidget` | Integrated into the Survey/Review/Edit workspace with blank-safe manual entry, explicit zero, point list, skip/previous navigation, Edit-only corrections, and five-point completion; expanded keyboard, focus, and locale audit remains in T11 |
| `LuminationProject` JSON | Version 1.1 reads legacy 1.0, stores stable resume/provenance fields, and uses separate app-data recovery snapshots |
| USB/Bluetooth sources | No synthetic physical-looking streams; generic serial is unverified, BLE discoveries are not treated as supported meters, and physical capture needs a verified profile |

## Decisions and ownership

1. Keep PySide6 as the implementation platform for this iteration.
2. Keep `LuminationProject` as the single project data authority and
   `WorkflowController` as the single workspace/action-policy authority.
3. Keep locally durable recovery separate from user-named project files.

Person 1 owns UI integration, translations, and presentation. Person 2 owns
project persistence, source/session contracts, and commands. Before shared-file
integration, both sides use this document as the event and data contract.
