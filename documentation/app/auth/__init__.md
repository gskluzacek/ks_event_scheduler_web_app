# app/auth/__init__.py

## Purpose
Marks `app.auth` as a package for modular authentication-related imports.

## NiceGUI and Web Feature Relevance
No direct UI code lives here, but this package boundary supports the split between:
- OAuth identity logic in `discord_oauth.py`
- Guild membership verification in `discord_guild.py`

That separation is important for page-level flows implemented with NiceGUI in `app/pages/auth.py` and `app/pages/players.py`.

## User Interaction Logic
No direct user interaction logic exists in this file.

## Current Limitations
- Empty module; no shared auth constants/utilities are exported.

## Existing Issues
- No direct issues found in this file.
