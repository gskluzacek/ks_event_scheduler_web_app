# app Directory Documentation Index

This index links to documentation for every Python file under `app/`.

## Root Files
- [__init__.md](__init__.md)
- [main.md](main.md)

## Subdirectories
- [auth/index.md](auth/index.md)
- [components/index.md](components/index.md)
- [models/index.md](models/index.md)
- [pages/index.md](pages/index.md)
- [utils/index.md](utils/index.md)

## Route to Module Cross-Reference
| Route | Page Documentation | Primary Dependencies |
|---|---|---|
| `/` | [main.md](main.md) | [pages/dashboard.md](pages/dashboard.md), [main.md](main.md) |
| `/dashboard` | [pages/dashboard.md](pages/dashboard.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [models/sample_data.md](models/sample_data.md) |
| `/accounts` | [pages/accounts.md](pages/accounts.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [components/timezone_select.md](components/timezone_select.md), [utils/filters.md](utils/filters.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/players` | [pages/players.md](pages/players.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [auth/discord_guild.md](auth/discord_guild.md), [utils/filters.md](utils/filters.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/timeslots` | [pages/timeslots.md](pages/timeslots.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [utils/filters.md](utils/filters.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/events` | [pages/events.md](pages/events.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/search` | [pages/search.md](pages/search.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/admin` | [pages/admin.md](pages/admin.md) | [components/layout.md](components/layout.md), [components/role_switcher.md](components/role_switcher.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/register` | [pages/auth.md](pages/auth.md) | [auth/discord_oauth.md](auth/discord_oauth.md), [components/timezone_select.md](components/timezone_select.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/register/complete` | [pages/auth.md](pages/auth.md) | [auth/discord_oauth.md](auth/discord_oauth.md), [components/timezone_select.md](components/timezone_select.md), [models/sample_data.md](models/sample_data.md), [models/schema.md](models/schema.md) |
| `/auth/discord/callback` (FastAPI) | [pages/auth.md](pages/auth.md) | [auth/discord_oauth.md](auth/discord_oauth.md), [main.md](main.md) |

## Full File List
- [__init__.md](__init__.md)
- [main.md](main.md)
- [auth/__init__.md](auth/__init__.md)
- [auth/discord_oauth.md](auth/discord_oauth.md)
- [auth/discord_guild.md](auth/discord_guild.md)
- [components/__init__.md](components/__init__.md)
- [components/layout.md](components/layout.md)
- [components/role_switcher.md](components/role_switcher.md)
- [components/timezone_select.md](components/timezone_select.md)
- [models/__init__.md](models/__init__.md)
- [models/schema.md](models/schema.md)
- [models/sample_data.md](models/sample_data.md)
- [pages/__init__.md](pages/__init__.md)
- [pages/accounts.md](pages/accounts.md)
- [pages/admin.md](pages/admin.md)
- [pages/auth.md](pages/auth.md)
- [pages/dashboard.md](pages/dashboard.md)
- [pages/events.md](pages/events.md)
- [pages/players.md](pages/players.md)
- [pages/search.md](pages/search.md)
- [pages/timeslots.md](pages/timeslots.md)
- [utils/__init__.md](utils/__init__.md)
- [utils/filters.md](utils/filters.md)
- [utils/storage.md](utils/storage.md)

## Notes
- These docs emphasize page features, NiceGUI usage patterns, user interaction logic, implementation limitations, and currently visible static issues.
- The issue sections are from static code review only (no runtime execution in this pass).
