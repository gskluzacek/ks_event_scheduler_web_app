# app/components/layout.py

## Purpose
Defines the shared page frame used by all major routes: top header, role switcher placement, nav buttons, and content container styling.

## Web Features and NiceGUI Usage
Important NiceGUI patterns:
- `@contextmanager`-based layout composition with `with layout.frame('/route')`.
- Shared header using `ui.header()` and nested `ui.row()` blocks.
- Dynamic nav generation from `NAV_ITEMS` metadata.
- Role-aware nav visibility through `role_switcher.is_at_least(...)`.
- Route highlighting for active nav item.
- Global table-header style injection via `ui.add_css(...)`.

This file demonstrates idiomatic Python-first NiceGUI composition instead of template inheritance.

## User Interaction Processing Logic
Interactions driven here:
- Clicking nav buttons triggers `ui.navigate.to(route)`.
- Role switcher render call injects account/role controls into header.

The function does not mutate data directly; it orchestrates navigation and top-level page structure.

## Current Limitations
- Global CSS is injected each page render and is not centralized in a single stylesheet file.
- Navigation configuration is static; no dynamic route discovery.
- Styling is tightly coupled to specific class strings (harder to theme globally).

## Existing Issues
1. Potential maintainability issue:
   - Static route tuples can drift from actual registered pages.
2. Potential UX issue:
   - Role-gated nav visibility is based on preview role semantics, not authenticated role assignments.
3. Styling scope issue:
   - Repeated style injection may be unnecessary overhead as the app grows.

## Suggested Improvements
- Move shared CSS to a centralized style resource.
- Add route consistency checks between `NAV_ITEMS` and registered page routes.
- Introduce a theme configuration object to reduce hardcoded style classes.
