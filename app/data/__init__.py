"""
Repository layer: one module per table, backed by app/db.py.

Every public function here is `async def` and wraps its blocking SQLModel/
sqlite3 call in `run.io_bound` internally, so page code can just
`await accounts.create_account(...)` without thinking about the event loop
each time (nicegui_llms.md Mental Model #7).

One module per table (every table has been migrated off the old in-memory
sample data) - see app/models/schema.py's module docstring.
"""
