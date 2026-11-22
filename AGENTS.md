# Working in Luxious

Luxious is a Python 3.10+ PySide6 desktop application. Read the
affected modules and tests before changing behavior. Keep physical measurements,
expected values, numerical reconstructions, and simulated meter data distinct.

## Project skills

Repository skills live in `.agents/skills/`. Read the matching `SKILL.md` and only
the supporting references needed for the task. The catalog and provenance are in
[docs/skills.md](docs/skills.md).

- Ideas and feature planning: `spec-kit-planning`.
- Module boundaries and architecture decisions: `architecture-designer`.
- Python implementation: `python-pro`.
- Desktop interface and map interaction: `frontend-craft`.
- Requested bitmap artwork: `image-studio`; scientific figures use project data
  and the numerical renderer.
- Requested API contracts: `api-designer`; FastAPI implementation, when selected:
  `fastapi-expert`.
- Requested agent pipelines: read `ecosystem-primer` first, then
  `langchain-fundamentals` or `langgraph-fundamentals`; use
  `langchain-dependencies`, `langgraph-persistence`, and
  `langgraph-human-in-the-loop` as needed.

## Applying upstream examples

User instructions and existing authorization take precedence over skill defaults.
Skills guide work within the requested scope. Example commands, frameworks,
providers, cloud services, credentials, and deployment steps are reference
material; their presence does not authorize installing or using them.
Verify version-sensitive APIs against current official documentation before using
upstream snippets in application code.

Preserve Python 3.10 compatibility unless a runtime upgrade is part of the task.
The Python skill's 3.11 examples, Poetry, strict mypy, formatters, and coverage
targets are optional guidance; follow the repository's actual tooling and use
verification proportionate to the change. Retain Qt threading and signal
conventions rather than mechanically converting desktop I/O to async code.

There is currently no HTTP backend or AI pipeline. Adding these skills does not
select a future service architecture. If agent work is requested, keep numerical
metrics deterministic, model suggestions distinguishable from measurements, and
external tracing or survey uploads within explicitly authorized scope.

## Verification

The existing test command is `python3 -m pytest -v tests/`. For Qt tests without a
display, use `QT_QPA_PLATFORM=offscreen`. Run checks relevant to the change and
report unavailable dependencies or unverified hardware or visual behavior.
