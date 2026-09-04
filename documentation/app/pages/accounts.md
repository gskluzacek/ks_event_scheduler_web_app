# app/pages/accounts.py

## Purpose
Implements Account Management page (`/accounts`) with role-aware filters, account table rendering, and manual account creation dialog.

## Web Features and NiceGUI Usage
NiceGUI patterns used:
- `@ui.page('/accounts')` route registration.
- `layout.frame('/accounts')` shared shell.
- `@ui.refreshable` sections for filter row and table.
- Conditional control rendering by role (name filter, kingdom/alliance filters, admin columns).
- Dialog-based account creation with reusable `TimeZoneSelector` component.
- Custom avatar table slot via Quasar template in `ui.table.add_slot`.

Feature highlights:
- SuperAdmin gets kingdom/alliance filters.
- Admin/PowerAdmin get name search and add account action.
- Plain users see their own account only.

## User Interaction Processing Logic
Major interaction flows:
1. Filter interactions:
   - selectors and search field update persistent filter values via `set_filter`
   - callbacks refresh filter controls and table
   - `_reconcile_filters()` removes invalid cross-filter combinations
2. Table rendering:
   - rows built from filtered in-memory accounts
   - optional admin columns shown for elevated users
   - optional helper hint for edit/remove behavior (not implemented)
3. Add account flow:
   - dialog validates required account name + timezone
   - appends `Account` record to seed list
   - refreshes filter + table to include new options/rows

## Current Limitations
- No true edit/remove actions despite UX hint text.
- No backend/service layer; direct append to module list.
- Filtering depends on player-derived alliance linkage because Account has no direct alliance relationship.
- All data operations occur client-triggered in the page module.

## Existing Issues
1. Scope correctness issue:
   - `_visible_accounts()` for Admin/PowerAdmin returns all accounts, not alliance-limited accounts as requirements imply.
2. Feature completeness issue:
   - Page suggests row edit/remove behavior but no row click handler exists.
3. Data coupling issue:
   - SuperAdmin kingdom/alliance filtering relies on player presence; accounts without players can be excluded unexpectedly.

## Suggested Improvements
- Add explicit account-to-alliance/ownership scoping rules.
- Implement edit/remove workflows with confirmations and validation.
- Introduce a service abstraction for account queries and mutations.
