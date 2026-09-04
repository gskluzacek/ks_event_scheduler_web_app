---
description: "Documentation reference for requirements, implementation notes, and design decisions. Use when clarifying product intent, role rules, and expected functional behavior before coding changes."
applyTo: "documentation/**"
---
# documentation - Product and Design Notes Reference

## Purpose
`documentation/` contains requirement narratives, implementation checkpoints, and historical notes that explain expected feature behavior beyond the source code itself.

## Key Files
| File | Purpose |
|---|---|
| `documentation/web_app_requirements.md` | Primary product requirements and domain model intent |
| `documentation/nicegui_llms.md` | NiceGUI implementation guidance for AI assistants |
| `documentation/admin_maint_features.md` | Admin and maintenance feature tracking notes |
| `documentation/todos.md` | Work backlog and task reminders |
| `documentation/UI_questions_redirection_corrections.md` | UI behavior clarifications and corrections |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Markdown | n/a | Human and agent-readable product context |
| DOCX references | n/a | Supplemental non-markdown docs stored in this folder |

## Patterns and Conventions
- Treat `web_app_requirements.md` as primary intent when behavior ambiguities appear.
- Keep implementation changes synchronized with requirements deltas.
- Use concise updates that identify affected modules and expected user impact.

## Notes for AI Agents
- Verify whether requirement text is aspirational versus implemented before asserting behavior.
- If code and docs diverge, flag the divergence and propose documentation updates.

## Entry Points and Key Commands
```bash
# No build command for this folder
# Use repository runtime commands when validating behavior:
uv run python -m app.main
```

## Cross-References
- `.github/copilot-instructions.md`
- `.github/instructions/app.instructions.md`
- `.github/instructions/architecture.instructions.md`

## Self-Healing
Validate file names and major requirement references on every load.
If docs move or are replaced, update this instruction file immediately.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
