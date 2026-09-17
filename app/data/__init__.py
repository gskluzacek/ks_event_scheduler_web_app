"""
Repository layer: one module per table, backed by app/db.py.

Every public function here is `async def` and wraps its blocking SQLModel/
sqlite3 call in `run.io_bound` internally, so page code can just
`await accounts.create_account(...)` without thinking about the event loop
each time (nicegui_llms.md Mental Model #7).

Only tables that have been migrated off app/models/sample_data.py get a
module here - see app/models/schema.py's module docstring for the migration
plan.
"""
