---
description: "Repository deprecation and legacy-area reference. Use when deciding whether to edit active runtime code versus historical artifacts, experiments, or archived patch content."
applyTo: "**"
---
# Deprecated and Legacy Features Reference

## Purpose
Tracks technologies, modules, and patterns that are no longer first-class implementation targets, or are intentionally historical/non-runtime.

## Current Status
No formal framework or language deprecations have been declared by the team.

## Legacy Areas
### Archived AI Patch Bundles
- What: `ai_authored_content/` stores historical patch files and prior generated iterations.
- Why: retained for traceability and experiments; not part of runtime execution.
- Affected paths: `ai_authored_content/**`
- Cleanup guidance: keep read-only unless explicitly curating historical artifacts.

### Discord OAuth PoC Script Area
- What: `discord_integration_poc/` contains standalone proof-of-concept code.
- Why: reference implementation history; the main app uses `app/auth/*` and `app/pages/auth.py`.
- Affected paths: `discord_integration_poc/**`
- Cleanup guidance: avoid production feature edits here unless intentionally updating PoC docs.

### NiceGUI Exploration Sandbox
- What: `nicegui_exploration/` provides isolated trial scripts.
- Why: quick prototyping and learning; separate from app runtime.
- Affected paths: `nicegui_exploration/**`
- Cleanup guidance: keep examples aligned with current NiceGUI usage patterns, but do not treat as production modules.

## Notes for AI Agents
- Prefer editing `app/**` for production behavior changes.
- If a legacy area is promoted to production usage, update this file and corresponding instruction files.

## Self-Healing
On load, verify that listed legacy paths still exist and still match their intended role.
If a listed path is removed or repurposed, update this file immediately.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
