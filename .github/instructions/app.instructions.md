---
description: "Python/NiceGUI application reference for pages, auth, models, and utilities. Use for UI route changes, role gating, filtering logic, Discord integration, and local behavior validation."
applyTo: "app/**"
---
# app - Python NiceGUI Application Reference

## Purpose
The `app/` package contains the executable Kingshot Scheduler mock application. It defines all page routes, shared layout components, Discord auth/guild integration helpers, in-memory domain models, and UI persistence utilities.

## Key Files
| File | Purpose |
|---|---|
| `app/main.py` | Application entry point and page/auth registration |
| `app/components/layout.py` | Shared header/nav frame and route-level visual scaffolding |
| `app/components/role_switcher.py` | Session-scoped role/account preview selection |
| `app/pages/auth.py` | Register pages and Discord OAuth callback flow |
| `app/auth/discord_oauth.py` | OAuth code/token/user exchange helpers |
| `app/auth/discord_guild.py` | Bot-token guild membership verification and result typing |
| `app/models/schema.py` | Dataclass domain schema and enums |
| `app/models/sample_data.py` | In-memory seed data backing all mock pages |
| `app/utils/filters.py` | Persistent filter/sort helper layer |
| `app/utils/storage.py` | Safe storage ID lookup and stale-ID protection |

## Tech Stack and Dependencies
| Package/Tool | Version | Purpose |
|---|---|---|
| Python | >=3.14 | Runtime language |
| nicegui | >=3.16.0 | UI and page routing |
| fastapi | >=0.141.1 | OAuth callback routing support |
| httpx | >=0.28.1 | Async Discord HTTP calls |
| python-dateutil | >=2.9.0 | Timezone offset computation |
| python-dotenv | >=1.2.3 | `.env` loading for auth helpers |

## Patterns and Conventions
- Route registration occurs by importing all `app.pages.*` modules in `app/main.py`.
- Shared page scaffold should always use `with layout.frame("/route")`.
- Role access checks are centralized in `role_switcher` helpers; do not duplicate ad hoc role logic.
- Stateful filters and sort preferences should route through `app/utils/filters.py`.
- OAuth identity and guild membership checks are intentionally separated into different modules.
- Sample data is shared process state and mock-only; preserve that assumption in docs and code comments.

## Notes for AI Agents
- Run app from repository root with module syntax.
- Do not claim persistence guarantees beyond process lifetime for sample data.
- Preserve security-sensitive OAuth state validation behavior in callback logic.
- Validate any new env vars by updating `.env.example` and this documentation.

## Entry Points and Key Commands
```bash
# Install dependencies
uv sync

# Run locally from repository root
uv run python -m app.main

# Optional runtime using plain Python
python -m app.main
```

## Cross-References
- `.github/copilot-instructions.md`
- `.github/instructions/architecture.instructions.md`
- `.github/instructions/documentation.instructions.md`

## Self-Healing
Agents reading this file must verify:
- Versions against `pyproject.toml`.
- Key file paths still exist under `app/`.
- Commands still match README and current runtime behavior.

If stale claims are found, fix this file first.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
