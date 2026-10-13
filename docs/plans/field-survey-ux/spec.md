# Field survey usability specification

Date: 13 October 2026. Status: proposed implementation scope. Baseline: `5e81ffd`.

## Purpose and users

Help a field worker or engineer prepare a room survey, record trustworthy lux readings, recover from interruptions, and hand over results with minimal navigation. Treat this as an offline instrument companion used on site. Technical experience varies; the design must respect experienced workers while making unfamiliar controls discoverable.

Assumed initial platform: the existing Qt desktop app on Windows laptops and touch-capable tablets; Linux remains a development preview. Mobile-native delivery is a separate decision. Likely contexts include glare, small screens, intermittent device connections, one-handed interaction, and interruptions. Confirm these assumptions with actual users before release.

## Current evidence

Source and the running sample interface show two large side docks, repeated panel titles, small text, many colored KPI cards, and an icon-heavy toolbar. `MainWindow` starts with populated sample measurements. USB reads generic serial text; Bluetooth readings are simulated. Table/dialog edits and CSV imports can bypass the command stack. `SurveyModeWidget` exists but is not wired into the current main window. The project format is JSON version 1.0; automatic recovery and a close-with-unsaved-work guard are absent in this checkout. Newer behavior described in `handoff.md` must be checked against source before implementation.

## Prioritized journeys

### US1 — Start or resume a job (P0)

Returning users open their project and resume at the next pending point. First-time users choose New survey and see three short steps: Room, Points, Readings. Training uses an explicitly labeled practice project.

Acceptance: creating a project never introduces measured demo values; setup can be navigated backwards without losing entries; manual entry works without a meter or internet. A worker can open an engineer-prepared survey without re-entering its geometry. Missing/replaced recent files offer Locate file and New survey.

### US2 — Record a point and continue (P0)

The survey screen shows the active point on the map, its ID and coordinates, reading source, live or manual value, and one Record & next action. The next pending point becomes active after a successful record.

Acceptance: explicit zero is valid; an untouched empty field cannot create zero. Repeated activation cannot accidentally apply the same capture event to two points. Live display changes alone never commit a reading. At the final point, show completion rather than wrapping to point one. Skipping remains visible as pending, and incomplete results remain labeled partial.

### US3 — Correct mistakes and handle interruptions (P0)

Workers can undo the last change, retake a reading, reconnect a meter, pause a survey, and resume after closing the app. Engineers can enter Edit and change points deliberately.

Acceptance: a failed retake keeps the previous recorded value; disconnects block meter capture and explain Reconnect or Enter reading; last known values are labeled stale. Done returns to the previous working state, including point, zoom, and source. Only authorized actions for the active mode can mutate the project, including shortcuts and table paths.

### US4 — Review and hand over (P1)

Workers see progress and basic results; engineers expand analysis, targets, expected values, and map controls. Users save or export a clearly identified complete or partial survey.

Acceptance: reports use measured data with pending counts visible; display precision changes never round stored readings; target claims identify the user-entered reference rather than claiming standards compliance. Demo content stays labeled in both screen and outputs. No export overwrites a file without the normal file-dialog confirmation.

## Requirements

| ID | Required behavior | Journey |
| --- | --- | --- |
| FR-01 | Start screen provides New survey, Open survey, available Resume, and secondary Try practice; no account or online setup | US1 |
| FR-02 | New surveys start with pending points; setup has at most three screens and visible editable defaults | US1 |
| FR-03 | One Survey workspace prioritizes next point, reading, record action, and progress; details remain available in Review | US2, US4 |
| FR-04 | Capture/manual entry binds to a specific point and source; pending, recorded zero, expected, and demo values remain distinct | US2 |
| FR-05 | Selected source is explicit and singular; capture requires a supported profile and a fresh valid sample; simulated sources are labeled practice | US2, US3 |
| FR-06 | Navigation does not write data; accidental double activation, lost source, and invalid input cannot create extra measurements | US2, US3 |
| FR-07 | Review, Survey, and Edit share a central action policy enforced in every mutation path | US2, US3 |
| FR-08 | Every user correction, clear, point change, and committed import is undoable; cancellable import preview is required | US3 |
| FR-09 | Atomic project saves, separate local recovery, unsaved-close protection, and explicit recorded/saved status prevent silent data loss | US1, US3 |
| FR-10 | Consistent tokens, readable text, generous targets, keyboard paths, visible focus, accessible names, and text alongside statuses | All |
| FR-11 | All new flows work in English, Romanian, and German; number entry accepts the applicable decimal separator | All |
| FR-12 | Maps, table alternatives, coverage labels, and partial-survey metrics preserve engineering meaning without relying on color alone | US2, US4 |
| FR-13 | Export defaults follow app language and project name; save and export failures preserve the working survey and provide a useful next action | US4 |
| FR-14 | Device reads and expensive reconstruction do not block entry; delayed results cannot replace a newer project revision | US2, US3 |

## Usability and accessibility acceptance

Use [ISO 9241-110 interaction guidance](https://www.iso.org/standard/75258.html) to structure task fit, understandable states, predictable behavior, learnability, control, and recovery. Use relevant [WCAG 2.2 criteria](https://www.w3.org/TR/WCAG22/) with [WCAG2ICT interpretation for native software](https://www.w3.org/TR/wcag2ict/). WCAG2ICT is informative guidance. This specification sets testable design targets; implementation and observed user evidence must precede any conformance claim.

| Gate | Product target | Evidence to collect |
| --- | --- | --- |
| G1: onboarding | At least 9 of 10 representative first-time participants record the first manual reading within two minutes without assistance, given dimensions and a prepared task; no tutorial required | Observed task trials; report raw counts, times, and supplied information |
| G2: repeated use | At least 9 of 10 complete a five-point run unaided; median software interaction overhead below five seconds per point, excluding walking and sensor settling | Timestamped observations and mistake counts |
| G3: recovery | All participants preserve prior readings during a scripted disconnect; at least 9 of 10 undo a mistaken entry or find manual fallback unaided | Disconnect/correction tasks; zero silent loss or false captures |
| G4: accessibility | Normal text contrast at least 4.5:1; essential control/focus graphics at least 3:1; complete keyboard path and meaningful accessible names | Contrast measurements; keyboard and native screen-reader walkthroughs |
| G5: sizing | At least 44 × 44 Qt logical px for common action hit areas, 48–56 px height for record/source actions, plus separation; point picking has an equivalent accessible list | Geometry inspection and touch trials; these are product targets, not CSS-pixel conformance claims |
| G6: layout/language | Usable at 960 × 600 and 1380 × 860; no lost essential actions at 100/150/200% DPI or enlarged text; all new EN/RO/DE flows complete | Screenshots and interaction checks at available logical sizes, scale factors, and locales |
| G7: integrity | Explicit zero persists; pending stays pending; corrections/undo/import preserve semantics; recovery restores durably acknowledged readings | Behavior checks and file round-trips, including write failure and interrupted save |
| G8: responsiveness | Immediate button/record feedback within 100 ms in normal use; current-view refresh target below 500 ms at 100 points; usable entry at 2,500 points | Measurements on a stated reference machine; slow analysis shows nonblocking status |

Recruit a mixed cohort of field workers and engineers, including less software-confident users. Assess actual tasks rather than assuming occupation predicts literacy or ability. Include left-handed use, keyboard-only use, and representative assistive-technology needs; use gloves only if supported by the target touchscreen. A small trial guides iteration and is not a statistical population guarantee.

## Edge cases and dependencies

Include: empty project; zero/blank/negative/decimal-comma input; overload or unknown units; same numeric value from distinct samples; stale sample after reconnect; selected point deleted; all points recorded; source switched mid-capture; two sources connected; pending imports; missing recent file; full disk; interrupted save; delayed interpolation; long translated labels; outliers; large grids; incomplete report.

Physical support claims require the exact meter model, protocol evidence, and real hardware trials. Meter freshness limits are profile-specific, not guessed from a universal timeout. Manual and practice onboarding can ship before physical integration. Confirm the existing company/site measurement plan, physical orientation, survey plane, and grid expectations rather than inventing standards-compliant defaults.
