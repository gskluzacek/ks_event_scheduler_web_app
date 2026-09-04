---
description: "Sandbox reference for NiceGUI exploration scripts and experiments. Use for prototyping UI concepts, validating widget behavior, and trialing table/grid patterns before production changes."
applyTo: "nicegui_exploration/**"
---
# nicegui_exploration - Experimental NiceGUI Reference

## Purpose
`nicegui_exploration/` is a sandbox for isolated NiceGUI experiments that are separate from the production mock application.

## Key Files
| File | Purpose |
|---|---|
| `nicegui_exploration/main.py` | Minimal hello-world style NiceGUI runner |
| `nicegui_exploration/editable_table.py` | Editable table behavior experiments |
| `nicegui_exploration/editable_ag_grid.py` | AG Grid style experimentation in NiceGUI context |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Python | >=3.14 | Runtime language |
| nicegui | >=3.16.0 | UI prototyping |

## Patterns and Conventions
- Keep experiments decoupled from `app/` production modules.
- Prefer concise, single-purpose scripts for behavior verification.
- Promote useful patterns into `app/` only after validation.

## Notes for AI Agents
- Do not treat these scripts as authoritative production architecture.
- If borrowing patterns, re-validate against actual `app/` constraints.

## Entry Points and Key Commands
```bash
# Run an exploration script
uv run python nicegui_exploration/main.py
```

## Cross-References
- `.github/instructions/app.instructions.md`
- `.github/instructions/documentation.instructions.md`

## Self-Healing
Verify listed scripts exist and still represent exploratory use.
If an exploration script becomes production-critical, update this file and remove ambiguity.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
