# app/pages/players.py

## Purpose
Implements Player Management page (`/players`) with role-aware visibility, multidirectional filters, sortable table rendering, and a guild-verified add-player workflow.

## Web Features and NiceGUI Usage
NiceGUI capabilities used extensively:
- page route + shared layout frame
- two `@ui.refreshable` regions (`player_filters`, `player_table`)
- dynamic select options recalculated from active filter state
- search field with live filtering
- Quasar avatar slot in table for guild/global Discord image fallback
- dialog workflow with progressive disclosure (verify first, then details)
- async verification callback against Discord guild membership helper

Feature highlights:
- role-based row visibility
- kingdom/alliance/account/name filters with reconciliation
- persistent filter + sort state
- add player requires successful guild membership verification

## User Interaction Processing Logic
Detailed interaction flow:
1. Page load computes visible players by role/account.
2. Filter row builds options based on other active filters.
3. On filter change:
   - persist selected value
   - reconcile invalid combinations
   - refresh filters and table
4. On name input change:
   - update stored query
   - refresh table only
5. Add Player dialog:
   - user selects kingdom/alliance
   - user verifies membership asynchronously
   - on success, detail fields become visible
   - submit appends `Player` with resolved role defaults and avatar fallback path
   - refreshes filters and table

## Current Limitations
- No edit/delete support for player records.
- No uniqueness checks for Kingshot ID per alliance/account.
- Direct list mutation instead of validated service layer.
- No pagination despite sortable table state persistence.

## Existing Issues
1. Input validation issue:
   - Add Player submit permits empty Kingshot ID/name because fields default to empty strings.
2. Authorization architecture issue:
   - Role preview mechanism controls visibility, but server-side write guards are minimal.
3. Data consistency issue:
   - No prevention of duplicate players or invalid cross-entity combinations beyond guild verification.

## Suggested Improvements
- Enforce required Kingshot fields and uniqueness checks.
- Add edit/remove workflows with permission checks.
- Introduce service layer with validation and persistence boundaries.
