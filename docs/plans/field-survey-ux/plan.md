# Luxious field survey frontend and onboarding plan

Date: 13 October 2026. Status: proposed. Read [spec.md](spec.md) for requirements and release gates, then [tasks.md](tasks.md) for ordered implementation. Planning uses the project-local frontend-craft and spec-kit-planning skills; architectural seams follow architecture-designer guidance.

## Design direction

Subject: a room-lighting instrument companion. Audience: workers conducting measurements on site and engineers preparing or reviewing those surveys. The interface should feel like reliable measurement equipment: clear readout, labeled controls, visible state, and quick repeatable actions.

The defining element is a large next-point readout paired with the highlighted location on the room map. Spend visual emphasis there. Use calm surfaces and restrained borders elsewhere; group controls by the job being performed. Images are unnecessary: retain existing vector icons and data-derived Matplotlib graphics. Do not manufacture scientific graphics with image generation.

This plan improves the existing PySide6 frontend. React and mobile wrappers remain separate options; no framework migration is needed to implement these flows.

## Baseline and priorities

The observed sample window gives excessive width to layers and KPI docks. It uses repeated titles, nested card borders, undersized text, and a different accent for many metrics. A worker has to infer where recording happens from icons and modal controls. Current sample startup, ambiguous device state, direct edit paths, and missing durable recovery are workflow issues to address alongside visual polish.

Order: trustworthy states and recovery; simple first-use flow; repeated measurement workspace; uniform visual treatment; engineer review/export; field usability evidence. A decorative reskin alone does not satisfy the specification.

## Start and onboarding

### Start screen

```text
Luxious                              Language: English
Room lighting survey

[Resume Office 201 — 8 of 12 recorded]  (when available)
[New survey]  [Open survey]

Try a practice survey                         Help
```

Resume is the primary action only when a valid saved/recovery project exists. Otherwise New survey leads. Show recent projects as a short file list, with date and progress where verified. Demo is secondary and labeled Practice in the workspace and exports. No sign-in, subscription, team setup, onboarding carousel, or mandatory product tour. Language is a readable choice from first launch and remains available later.

### Three setup screens

| Step | Required interaction | Details disclosed when needed |
| --- | --- | --- |
| 1. Room | Enter length and width, or use a prepared project; show a labeled rectangle | Proposed room name; visible measurement-height/margin summary with Change; optional notes |
| 2. Points | Choose rows and columns, inspect point count, first point, and walking direction | Exact spacing, custom placement, and optional target belong in Survey details |
| 3. Readings | Choose Enter readings or Connect a meter; see a final room/grid/source summary | Known device/profile selection; port/baud only under Connection details |

Back preserves work. Each screen has one clear Continue/Start survey action and inline field errors. No hidden conversion of guessed defaults into requirements: survey height, margins, and grid choices are visible and editable, preferably supplied by the engineer's job file. Optional targets start unset. Import file is an alternate setup route with column mapping and spatial preview, not an additional mandatory screen.

For manual entry, a short contextual instruction appears at P1: "Stand at the highlighted point. Enter the meter reading, then select Record & next." It can be dismissed and reopened through Help. Device users see "Place the sensor at P1, then record the live reading." Neither path requires knowing interpolation, uniformity, or the app's schema.

## Main workspaces

### Survey: record with minimal navigation

```text
Office 201       6.0 × 4.0 m     8 of 12 recorded
[Survey] [Review]                Meter: receiving readings

┌─────────────────────────────────────┬─────────────────────┐
│                                     │ NEXT POINT          │
│             Room map                │ P9   x 1.13, y 1.00 m│
│       orientation + next point      │                     │
│       recorded/pending symbols      │ LIVE: 448 lx         │
│                                     │ USB — device name   │
│                                     │ [Record & next]     │
│                                     │ [Previous] [Skip]   │
│                                     │ [Correct reading]   │
└─────────────────────────────────────┴─────────────────────┘
Recorded P8: 442 lx       [Undo]       Saved locally 11:42
```

Keep the map roughly two-thirds of the available workspace with a 280–320 logical px action pane at default width; adapt rather than enforce this ratio at small sizes. Hide map configuration until requested through a labeled Map settings control. Do not hide acquisition status in a tiny footer. The record button remains in one stable location, with a large hit area, text, and an optional icon.

Manual input replaces LIVE with a labeled editable Reading (lx) field, initially empty for pending points. Explicit zero works. Record advances to the next pending point; Skip advances without writing and leaves the point pending. Previous is navigation only. Correct reading enters Edit with the current point selected. After Done, restore the prior workspace, point, zoom, and source.

Separate sensor placement from capture. The map shows a clear orientation marker matching the setup preview, point ID, and coordinates; the accessible point list offers the same selection without precision clicking. Highlight first/next points and optional route arrows without making animation necessary. At completion show "12 of 12 recorded" with Review results and Save/export. At partial completion show exactly what remains and permit a labeled partial export.

### Review and deliberate edits

```text
Office 201    8 of 12 recorded — partial    [Survey] [Review]

Average 448 lx | Lowest 320 lx | Highest 570 lx | Uniformity 0.71
Measured points: 8   Pending: 4

┌─────────────────────────────────────┬─────────────────────┐
│              Room map               │ [Readings] [Analysis]│
│              lux legend             │ Table or details    │
│                                     │                     │
└─────────────────────────────────────┴─────────────────────┘
[Map settings]  [Edit points]                   [Save/export]
```

Show the four core results once, with clear units and counts. Advanced statistics, target/reference comparisons, expected values, interpolation method, contour interval, and export precision live under Analysis or Map settings. Uniformity gets a short explanation on demand; engineers retain exact values and original readings. Do not assert pass/fail unless a defined reference and assessment scope support it.

Edit is an explicit temporary state with a visible Edit label and Done. Add/delete/move/clear/retake are available there through labeled actions and undo. Survey and Review mutation permissions are centrally enforced. This is workflow disclosure, not a worker/engineer role-selection screen or access-control system.

## Device and saving states

Present connection and data readiness separately. A port opening is "Connected — waiting for a reading", not proof that a supported meter is delivering data.

| State | User sees | Next action |
| --- | --- | --- |
| Manual | Enter readings | Type a value, Record & next |
| Connecting | Connecting to device… | Cancel; controls remain responsive |
| Receiving | Device name, fresh value, source | Record & next |
| Stale / disconnected | Last value marked stale; capture unavailable | Reconnect or Enter reading |
| Unsupported | This meter profile is not supported | Enter reading; Connection details/help |
| Practice | Practice — simulated readings | Practice capture; unmistakable demo label |
| In memory | Recorded P7; changes not yet saved | Normal operation with explicit save status |
| Durable recovery/save | Saved locally, with timestamp | Continue; user can choose named Save as |
| Save failed | Reading recorded; could not save locally | Retry or Save as; preserve in-memory readings |

Examples: "Meter disconnected. P7 has not been recorded. Reconnect or enter the reading." "Enter a number, for example 420.5 lx." "File could not be saved. Choose another location." Errors identify the affected action and keep the current point/value. Avoid modal alerts for every successful capture; use persistent inline feedback. Sound is optional and never the only confirmation.

## Visual tokens and consistency

| Token | Proposed value | Purpose |
| --- | --- | --- |
| Background | `#F4F6F8` | Workspace |
| Surface | `#FFFFFF` | Reading pane, dialogs |
| Text | `#17212B` | Primary text |
| Supporting text | `#52606D` | Secondary labels |
| Action | `#1D4ED8` | Primary action, focus, selection |
| Boundary | `#C5CDD7` | Restrained nonessential separators |

Semantic status accents: success `#166534`, warning `#92400E`, failure `#B91C1C`, always accompanied by words and/or shape. Validate each actual foreground/background pairing; a decorative boundary is not the sole indication of a control. Essential outlines need sufficient contrast against their surface.

Use one system sans-serif family: Segoe UI on Windows with the OS sans-serif fallback. Body 11–12 pt, supporting text at least 10.5 pt, section headings 14–16 pt, active reading 24–32 pt; inherit OS/DPI scaling and support enlarged text. Use semibold sparingly. Left-align labels and copy; align numeric table columns consistently.

Spacing: 4, 8, 16, 24, 32 logical px. One 6 px corner radius for ordinary controls/panels. One outline per container, no nested result-card boxes or striped label backgrounds. Normal actions have at least 44 × 44 logical px hit areas; record/source actions are 48–56 px tall, with room for translated labels and adjacent-button separation. Prefer click-release activation over pointer-down writes. Do not claim glove suitability until tested with the target hardware.

Keep the screen still while recording: no entrance animations, no celebratory overlays, no hover-dependent instructions. A short optional selection transition must respect reduced-motion preferences; essential state changes work without it. Replace underscored/duplicated headings with Map settings, Results, Readings, and Analysis. Format all visible lux values consistently while retaining full precision in data and engineering detail views.

## Native accessibility and field usability

Use relevant [WCAG 2.2](https://www.w3.org/TR/WCAG22/) criteria with [WCAG2ICT native-software guidance](https://www.w3.org/TR/wcag2ict/), implemented through [Qt widget accessibility](https://doc.qt.io/qt-6/accessible-qwidget.html). Provide labels, accessible names/values, keyboard focus and a logical tab order; status changes need an accessible announcement without repeatedly speaking every live sample. Preserve focus on errors and predictable context changes. Provide reading-table equivalents for map information and selection.

Enter records only within the active valid reading flow; it must not turn a pending untouched value into zero or submit an unrelated dialog. Space activates focused buttons normally; any additional capture shortcut must be scoped to the survey workspace and inactive while editing text. Escape cancels transient actions or exits Edit, preserving recorded work. Ctrl+Z/Ctrl+Y, Ctrl+S, and standard file shortcuts remain discoverable. Do not assign Ctrl+X to redo, because users expect Cut.

For 960 × 600, keep source, point, input, record, and progress visible; allow secondary content to scroll/collapse. At enlarged text or high DPI, simplify the composition before shrinking fonts. Verify Windows screen-reader behavior and keyboard operation on the intended release platform; the Matplotlib canvas alone is not an accessible substitute for the point list. EN/RO/DE labels must fit without abbreviating essential instructions.

## Technical plan and proposed decisions

Keep `LuminationProject` as the shared project data and deterministic analysis as the metric source. Introduce only seams needed for this workflow:

- `ui/workflow_controller.py`: current workspace/edit return state, selected point, navigation, and action permissions. All table, dialog, shortcut, and canvas mutations go through the same policy and commands.
- `measurement_sources/device_session.py`: explicit selected source, connection state, supported profile, latest sample identity/unit/time, capture eligibility, and disconnect events. Freshness uses monotonic time/profile limits; persistent timestamps describe recorded samples. Transport and capture lifetimes stay independent of workspace changes.
- Existing `utils/undo_commands.py`: extend correction/grid/import commands with before/after state and one successful-refresh path. Failed/cancelled actions do not enter history.
- `persistence/project_io.py` plus a small recovery coordinator: atomic named saves and separate app-data recovery snapshots. Preserve original files, visible data status, and legacy version 1.0 loading. Persist minimal resume state and manual/device provenance through an explicit versioned extension; never serialize live transport objects or auto-reconnect devices on load. Record the migration before changing the schema.
- `ui/start_screen.py`, `ui/dialogs/survey_setup_dialog.py`, and the existing `ui/survey_mode_widget.py`: start, setup, and repeated entry. Reuse suitable dialogs and widget behavior instead of rebuilding unaffected analysis.
- `ui/styles.py`: shared tokens with per-widget exceptions removed. Existing map rendering retains physical scale, units, coverage, and legends. Expected/difference rendering and nearest fallback need correction before those views are presented as reliable.

Proposed decisions: retain native Qt for this iteration; use one application-state owner and one selected capture source; use locally durable recovery separate from named projects. Benefits are focused implementation and predictable behavior. Costs include persistence migration, hardware qualification, and maintaining both basic and advanced presentations. Broad service extraction or a React rewrite adds work without being necessary for the stated UI objective; revisit it if cross-platform product scope is approved.

UI feedback and hardware I/O must remain responsive. Cache reconstruction by data/settings revision; selection/hover only redraw selection. Profile before adding worker computation; if necessary, discard outdated results and marshal updates to the Qt UI thread. Recovery must not claim Saved before its write succeeds or show success after an error.

## Verification and release sequence

Use the gates in spec.md. First validate manual/practice onboarding and capture semantics with a clickable native prototype. Then connect the selected supported physical meter and verify stale/disconnect/reconnect behavior. Apply visual tokens and review/export presentation once those states are stable. Run behavior checks for data-changing work, native visual/accessibility checks, and real-user task trials. Observe field workers and engineers before finalizing defaults; do not infer success from screenshots alone.

Review screenshots at 960 × 600, 1380 × 860, and a larger/touch configuration, with normal and enlarged text. Record viewport, DPI, OS, language, device/profile, and reference machine. Ship an offline manual workflow independently if physical compatibility is unverified; device-specific onboarding becomes available only with a qualified adapter.

Open evidence to obtain: actual target devices/OS and touchscreen capability; one exact USB/BLE meter model; representative job grids and survey height; real worker/engineer observations; initial export defaults. These do not prevent starting the manual workflow prototype and shared token work.
