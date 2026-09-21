# app/pages/players.py

## Purpose
`/players`, titled **Accounts & Players**: one page that shows accounts and, nested under each, that account's players. (It replaced
separate Accounts and Players pages.)

## Layout
- Account-first: a card per visible account with its name, time zone, Discord username and player count, plus **View**, **Edit** (only
  where `_can_edit_account`) and **Add Player** buttons, and an expander for the account's player cards. An account with no players
  gets a disabled expander with a tooltip. With nothing visible the page says "No data available".
- Accounts are paginated (5 per page); the expanded state, current page, filters and sort are saved per browser (see
  [../utils/filters.md](../utils/filters.md)).
- Player cards show avatar (guild avatar, else the account's global avatar, else a generic icon), name, town center level, kingdom,
  alliance, Kingshot id, power, time slot count, Discord nickname and, for PowerAdmin and above, roles - with **View** and **Edit**.
- SuperAdmin also gets **Add Account** (a manual account).

## Filters
Kingdom, Alliance, Account name (admin roles) and Kingshot name. Kingdom and Alliance options come only from the players the viewer
can see and narrow each other in both directions; the name boxes don't change the dropdown options. They are built with
`safe_select`. The kingdoms and alliances are read from the database once per render and passed to pure helpers (`_narrow`,
`_active_filters`, ...).

## Visibility (current behavior)
- SuperAdmin: every account and player.
- Admin/PowerAdmin: every account (view only), but only players in alliances they belong to.
- User/SchedulerAdmin: only their own account and its players.

## Player dialogs
- **View** - every player column with audit ids resolved to names.
- **Edit** - editable: Kingshot name, power, town center level, and (SuperAdmin/PowerAdmin) roles; the Discord nickname and guild
  avatar change only through "Sync from Discord" (bot-token check). A PowerAdmin can't edit their own roles.
- **Add Player** (from an account card) - pick Kingdom, then Alliance (narrowed to that kingdom; Admin/PowerAdmin only see their
  own alliances), then **Verify Guild Membership** (enabled once both are chosen); the detail fields appear and **Add Player** is
  enabled only after a successful check. Manual accounts skip verification. The creator is recorded (null when adding to your own
  account).

Slot counts come from one grouped query (`count_time_slots_by_player`). See also [account_player.md](account_player.md) and
[accounts.md](accounts.md).
