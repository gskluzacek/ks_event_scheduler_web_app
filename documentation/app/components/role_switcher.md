# app/components/role_switcher.py

## Purpose
Implements a mock account/role switching control for previewing role-gated page behavior without full authentication/authorization infrastructure.

## Web Features and NiceGUI Usage
NiceGUI patterns used:
- Uses `app.storage.user` for per-browser-session persistence.
- Renders header controls with `ui.row`, `ui.select`, `ui.icon`, and `ui.label`.
- Registers `on_value_change` callbacks on account/role selectors.
- Uses `ui.navigate.reload()` to force route rebuild under new role context.

This component is reused from the shared layout and therefore influences every page.

## User Interaction Processing Logic
Interaction flow:
1. User changes account or role in dropdowns.
2. Callback updates session storage keys:
   - `preview_account_id`
   - `preview_role`
3. Page reload occurs to recompute visibility, filters, and data scope.
4. Special sentinel option routes user to registration page without persisting invalid account.

Helper functions (`current_role`, `is_at_least`, `is_any_admin`) provide role predicates used throughout page logic.

## Current Limitations
- This is a mock mechanism and not real role assignment/auth.
- Depends on sample data remaining present.
- Uses full page reload for state transition rather than selective refresh.

## Existing Issues
1. Stability issue:
   - `current_account_id()` assumes `accounts[0]` exists; empty account list would raise an exception.
2. Security-model issue:
   - Role preview can elevate capabilities in UI without true backend authorization checks.
3. Scalability issue:
   - Full page reload on each role/account change can be heavy for larger pages.

## Suggested Improvements
- Add fallback behavior when account list is empty.
- Decouple mock preview from production authorization paths.
- Consider partial refresh patterns for smoother transitions.
