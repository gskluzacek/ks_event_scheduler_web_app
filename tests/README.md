# Tests

Run everything with `uv run pytest` (a single file: `uv run pytest tests/test_timeslots_page.py`). pytest, pytest-asyncio and NiceGUI's
`user` fixture are configured in `pyproject.toml` (`[tool.pytest.ini_options]`, dev dependency group).

## How it is set up (`conftest.py`)
- **A fresh database per test.** The autouse `database` fixture points `app.db.engine` at a new SQLite file in pytest's temp
  directory and loads the four preview seeds: accounts 1001-1005, kingdoms 4001-4002, alliances 2001-2006, players 3001-3012,
  events 5001-5007, time slots 6001-6016. No time zones are seeded (the setup wizard loads them); tests that need some insert their
  own. The real `kingshot.db` is never opened.
- **NiceGUI session files** go to a temp folder (`NICEGUI_STORAGE_PATH`), not `.nicegui/`.
- `as_super_admin` acts as the SuperAdmin preview role (account 1001).

## Files
| File | Covers |
|---|---|
| `test_db_layer.py` | seeds, enforced foreign keys, CHECK/UNIQUE constraints, the no-overlap time slot triggers, the repositories |
| `test_slot_times.py` | the end-minus-one-second time conversions |
| `test_players_page.py` | Accounts & Players page: filters, add-player dialog, player details, slot counts |
| `test_timeslots_page.py` | Time Slots page: table, Status filter, View/Add/Edit, the `confirmed_ind` rules, overlaps |
| `test_events_page.py` | Events page: list, Create Event and its constraints, publish toggle |
| `test_admin_page.py` | Site Maintenance: kingdoms, alliances and time zones |
| `test_search_and_dashboard.py` | Search and Dashboard reading the DB |
| `test_stale_ids.py` | stale saved ids: fresh-DB session clearing, clear-on-switch, `safe_select`, pages surviving stale ids |

## Writing a page test
- The `user` fixture is a simulated browser. It **resets the route table for every test**, so a page test module re-imports the page
  modules it needs in an autouse `routes` fixture (`sys.modules.pop(...)`, then `importlib.import_module(...)`). Small test-only
  pages (for example one that opens a dialog for a given id) are defined there too.
- Find elements with `user.find(kind=...)` and drive them with `helpers.py` (`button`, `selects`, `newest`, `icon_buttons`).
  A rejected submit leaves its dialog open, so use `newest(...)` to reach the latest dialog's fields.
- Change handlers run asynchronously: after `set_value(...)` or a click, `await asyncio.sleep(0.3-0.5)` before asserting.
- `act_as(monkeypatch, role, account_id)` sets the previewed role and account.
- Discord calls (guild verification, refresh) are not exercised: they need the network.
