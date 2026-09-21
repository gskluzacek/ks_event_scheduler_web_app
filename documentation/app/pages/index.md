# app/pages Index

One module per page (importing it registers its `@ui.page` routes), plus helpers shared by the account/player pages.

- [__init__.md](__init__.md)
- [dashboard.md](dashboard.md) - `/dashboard`
- [players.md](players.md) - `/players` (Accounts & Players)
- [account_player.md](account_player.md) - visibility/edit rules and dialog helpers shared by `players` and `accounts`
- [accounts.md](accounts.md) - account view/add/edit dialogs and the Discord refresh (no route of its own)
- [timeslots.md](timeslots.md) - `/timeslots`
- [events.md](events.md) - `/events`
- [search.md](search.md) - `/search`
- [admin.md](admin.md) - `/admin` (Site Maintenance, SuperAdmin only)
- [auth.md](auth.md) - `/register`, `/register/complete`, `/auth/discord/callback`
- [setup.md](setup.md) - `/setup` first-run wizard
