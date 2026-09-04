---
description: "Reference for archived AI-authored patches and iteration history. Use for traceability, patch archaeology, and context when comparing historical generated changes."
applyTo: "ai_authored_content/**"
---
# ai_authored_content - Archived Patch History Reference

## Purpose
`ai_authored_content/` stores generated patch artifacts and historical change batches. It is a reference archive, not an active runtime module.

## Key Files
| File | Purpose |
|---|---|
| `ai_authored_content/**` | Historical patch artifacts grouped by feature/round |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Patch files / markdown context | n/a | Historical change tracking |

## Patterns and Conventions
- Preserve folder organization by feature and round.
- Avoid editing archived patches unless curating history explicitly.

## Notes for AI Agents
- Do not apply archived patches blindly to current code.
- Treat this area as historical context only.

## Entry Points and Key Commands
```bash
# No direct runtime entry points in this folder
```

## Cross-References
- `.github/instructions/deprecated-features.instructions.md`
- `.github/copilot-instructions.md`

## Self-Healing
Verify this folder remains non-runtime archival content.
If artifacts are promoted into active workflows, document the transition here.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
