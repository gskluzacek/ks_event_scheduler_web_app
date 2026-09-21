# app/pages/accounts.py

## Purpose
Account dialogs and mutations. There is **no** `/accounts` route: these are launched from the account cards on `/players`.

## Contents
- `_open_view_account_dialog(account)` - read-only view of every account column; audit ids are shown as account names and times in
  the account's time zone.
- `_open_edit_account_dialog(account, on_saved=...)` - the same read-only detail, then an editable section. A **manual** account can
  change its name; a **Discord** account can't change its name but has a "Refresh from Discord" button (below). Both can change the
  time zone (region and location dropdowns). A SuperAdmin editing someone else's account also gets an `is_super_admin` control.
- `_do_discord_refresh(...)` - re-fetches the Discord identity with the stored refresh token and fills the still-open dialog; the user
  must click Save to keep it. Rate limited to 10 per 4 hours per acting session and target account (`utils/rate_limit.py`). Outcomes:
  success, no stored credentials, re-authorization needed, or error.
- `_open_add_account_dialog(on_added=...)` - SuperAdmin only: creates a manual account (name and time zone).

Callers pass an `on_saved`/`on_added` callback instead of these functions refreshing containers themselves, which avoids a circular
import with `players.py`.
