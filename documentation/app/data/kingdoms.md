# app/data/kingdoms.py

Repository for `kingdom`.

- `list_kingdoms()` - ordered by `kingdom_id`
- `get_kingdom(kingdom_id)`
- `create_kingdom(name=, create_account_id=None)` - raises `IntegrityError` if the name is already used.
