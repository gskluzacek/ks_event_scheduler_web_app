---
description: "Reference for standalone Discord OAuth and guild-verification proof-of-concept code. Use for auth-flow comparison, integration debugging, and understanding historical implementation decisions."
applyTo: "discord_integration_poc/**"
---
# discord_integration_poc - Discord OAuth PoC Reference

## Purpose
`discord_integration_poc/` contains a standalone PoC implementation of Discord OAuth and guild membership verification used as a precursor/reference for the main app integration.

## Key Files
| File | Purpose |
|---|---|
| `discord_integration_poc/discord_oauth_poc.py` | Standalone NiceGUI+FastAPI OAuth callback and bot membership verification flow |
| `discord_integration_poc/.env.example` | PoC-specific environment variable template |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Python | >=3.14 | Runtime language |
| nicegui | >=3.16.0 | PoC UI/server shell |
| fastapi | >=0.141.1 | Callback route support |
| httpx | >=0.28.1 | Discord API calls |
| python-dotenv | >=1.2.3 | Local env loading |

## Patterns and Conventions
- Treat this folder as reference-only unless explicitly tasked to improve PoC.
- Mainline auth behavior should be implemented under `app/auth` and `app/pages/auth.py`.

## Notes for AI Agents
- Changes in this folder do not automatically impact `app/` runtime.
- Preserve clear separation between OAuth identity and guild membership validation concerns.

## Entry Points and Key Commands
```bash
# Run standalone PoC
uv run python discord_integration_poc/discord_oauth_poc.py
```

## Cross-References
- `.github/instructions/app.instructions.md`
- `.github/instructions/deprecated-features.instructions.md`

## Self-Healing
Verify file paths and env-var assumptions on every load.
If PoC behavior drifts from its documented purpose, update this file.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
