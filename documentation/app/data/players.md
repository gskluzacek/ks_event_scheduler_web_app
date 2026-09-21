# app/data/players.py

Repository for `player` and `player_role`. Roles are not a column of `Player`; they live in `player_role` and are read
with `roles_by_player_id()` and written by passing `roles=` to `create_player()`/`update_player()`.

- `list_players(account_ids=None, alliance_ids=None)` - ordered by `player_id`; each filter is skipped when `None`.
- `get_player(player_id)`
- `create_player(account_id=, alliance_id=, kingshot_id=, kingshot_name=, power=, town_center_level=, discord_nickname=None, discord_guild_avatar_url=None, roles=None, create_account_id=None, update_account_id=None)` -
  `roles` defaults to `[Role.USER]`.
- `update_player(player_id, update_account_id=, roles=None, **fields)` - `roles`, when given, replaces the whole role set
  in the same transaction.
- `delete_player(player_id)` - also deletes the player's roles and time slots (`time_slot.player_id` is an enforced FK).
- `roles_by_player_id(player_ids=None)` - one query returning `{player_id: [Role, ...]}`.
