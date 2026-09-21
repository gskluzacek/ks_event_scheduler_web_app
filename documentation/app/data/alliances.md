# app/data/alliances.py

Repository for `alliance`.

- `list_alliances(kingdom_ids=None)` - ordered by `alliance_id`; `None` means all, an empty collection matches nothing.
- `get_alliance(alliance_id)`
- `create_alliance(kingdom_id=, name=, discord_guild_id=, discord_guild_name=, create_account_id=None)` - raises
  `IntegrityError` if the kingdom doesn't exist, the name is used within that kingdom, or the Discord guild already
  belongs to another alliance (one guild per alliance).
