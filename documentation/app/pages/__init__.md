# app/pages/__init__.py

## Purpose
Package marker. `app/main.py` imports each page module; importing is what registers its routes. `accounts.py` and
`account_player.py` have no route - they are imported by `players.py`.
