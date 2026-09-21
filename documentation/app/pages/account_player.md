# app/pages/account_player.py

## Purpose
Helpers shared by the Accounts & Players page ([players.md](players.md)) and the account dialogs ([accounts.md](accounts.md)).

## Contents
- `_format_dt(dt, iana_name)` - a UTC timestamp shown in an account's time zone.
- `_render_field()`, `_render_copyable_field()` - label/value rows for the View and Edit dialogs (the copyable one truncates a long
  Discord avatar URL, shows the full value in a tooltip and adds a copy button).
- `_set_enabled(element, enabled)` - toggles Quasar's `disable` prop.
- `_resolve_account_name(id, owner)` - turns an audit column into an account name (a null creator means the account's own name).
- `_visible_accounts()` - Admin, PowerAdmin and SuperAdmin see every account; a User or SchedulerAdmin sees only their own.
- `_can_edit_account(account_id)` - your own account, or any account if SuperAdmin.
- `_admin_alliance_ids()` - the alliances the viewer's own players belong to (used to scope Admin/PowerAdmin/SchedulerAdmin).

These rules are the current behavior; they are under review pending the per-role, per-screen matrix.
