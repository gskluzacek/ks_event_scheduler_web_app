# app/components/role_switcher.py

## Purpose
A **development-time** stand-in for real login and role assignment: the header's "Previewing as" account and role
dropdowns. The previewed account and role are saved in `app.storage.user` (`preview_account_id`, `preview_role`). It is
planned to disappear once real login exists, which also removes the preview half of the stale-id handling.

## Contents
- `load_accounts()` - fetches the account list once per page load (`layout.frame()` calls it) and keeps it in
  `app.storage.client`, so the synchronous helpers below can read it from anywhere, including button handlers.
- `current_account_id()` - the saved account id, falling back to the first account if it's missing or no longer exists
  (via `get_valid_id`).
- `current_role()` - the saved role (default `User`).
- `is_at_least(*allowed)` - True if the current role is one of `allowed` **or SuperAdmin**.
- `is_any_admin()` - True for Admin, PowerAdmin, SchedulerAdmin or SuperAdmin.
- `render()` - draws the two dropdowns (built with `safe_select`). Choosing "- New User (not registered) -" navigates to
  `/register` without saving anything. Changing either dropdown calls `clear_page_state()` (the previous view's saved
  filters, sorting and paging no longer apply), saves the new values and reloads the page.

## Notes
Roles here are a preview only; nothing is enforced server-side yet.
