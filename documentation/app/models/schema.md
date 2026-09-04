# app/models/schema.py

## Purpose
Defines the in-memory domain model for the application using dataclasses and enums:
- roles and account types
- core entities (Account, Player, Event, TimeSlot, Kingdom, Alliance, TimeZone)
- helper ID generator

## Web Features and NiceGUI Usage Context
This file does not render pages directly, but every NiceGUI page relies on these structures for:
- table row shaping
- form field expectations
- role-based behavior checks
- scheduling/time-slot display semantics

The model structure is tightly coupled with page workflows in `app/pages`.

## User Interaction Processing Logic Impact
Dataclass fields define what interactions are possible:
- registration creates `Account`
- add player dialog creates `Player`
- event management creates `Event`
- time-slot management creates `TimeSlot`

Enums (`Role`, `TimeSlotType`, `AccountType`) drive selectable options and branch logic in UI callbacks.

## Current Limitations
- IDs are generated in-process with `itertools.count`, so they reset on restart.
- No validation hooks for entity invariants (e.g., event date range, time-slot overlap, cross-alliance constraints).
- Dataclasses are mutable and globally shared in this mock architecture.
- UTC/local conversion rules are not centralized for all datetime operations.

## Existing Issues
1. Persistence limitation:
   - ID and entity state are non-durable and restart-sensitive.
2. Integrity limitation:
   - No built-in model-level constraints to prevent invalid combinations.
3. Concurrency limitation:
   - Shared mutable lists are vulnerable if app later scales across workers.

## Suggested Improvements
- Move to a persistent data layer with database-generated IDs.
- Add validation logic at model/service layer.
- Introduce typed DTOs and conversion boundaries for UI payloads.
