# app/db.py

## Purpose
The SQLite engine and session helper. The database file is `kingshot.db` at the repository root (git-ignored).

## Contents
- `engine` - SQLAlchemy engine for `kingshot.db`. A connect listener (`enable_foreign_keys`) runs
  `PRAGMA foreign_keys=ON` on every new connection, because SQLite ignores FOREIGN KEY constraints otherwise.
- `init_db()` - `SQLModel.metadata.create_all(engine)`; safe on every startup. Returns `True` if the database file did
  not exist before the call. `create_all` never alters an existing table, and there is no migration tool, so a schema
  change to an existing table means deleting `kingshot.db` and re-running setup and the seeds.
- `get_session()` - a new `Session`. Pages never call this; they go through the repositories in `app/data/`.

## Why the repositories are async
The SQLite driver is synchronous and would block NiceGUI's single event loop, so each repository function runs its
query inside `nicegui.run.io_bound`.
