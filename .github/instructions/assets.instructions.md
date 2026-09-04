---
description: "Reference for static asset files used by UI prototypes and demos. Use when adding, replacing, or tracing image resources consumed by mock interfaces."
applyTo: "assets/**"
---
# assets - Static Resource Reference

## Purpose
`assets/` contains static media used by mock pages and experiments.

## Key Files
| File | Purpose |
|---|---|
| `assets/ed_norton_fight_club.jpg` | Example static image asset used by prototypes |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Static image assets | n/a | UI/media resources |

## Patterns and Conventions
- Keep assets lightweight and appropriately licensed.
- Reference assets by stable relative path from consuming code.

## Notes for AI Agents
- Confirm file existence before wiring references.
- Do not store sensitive data in assets.

## Entry Points and Key Commands
```bash
# No executable commands for this folder
```

## Cross-References
- `.github/instructions/app.instructions.md`
- `.github/copilot-instructions.md`

## Self-Healing
Validate that listed assets still exist and are still used as described.
Update this file when assets are added, renamed, or removed.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
