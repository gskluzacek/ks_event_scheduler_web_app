# app/data/accounts.py

Repository for `account`.

- `has_any_account()` - is there at least one account? (used by the setup gate and the wizard)
- `list_accounts()` - all accounts ordered by `account_name`
- `get_account(account_id)`
- `create_account(account_type=, account_name=, time_zone=, is_super_admin=False, create_account_id=None, **discord_fields)` -
  `discord_fields` are the Discord-only columns (id, username, global name, avatar URL, OAuth tokens and expiry); omit
  them for a manual account. Raises `IntegrityError` on a duplicate `account_name` or `discord_user_id`.
- `update_account(account_id, update_account_id=, **fields)` - updates the given columns plus the audit columns.
