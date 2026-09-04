# app/pages/__init__.py

## Purpose
Marks `app.pages` as a package and supports side-effect route registration when modules are imported by `app/main.py`.

## NiceGUI and Web Feature Relevance
Although empty, this file supports the route bootstrap pattern:
- importing `app.pages.*` executes each `@ui.page` decorator
- resulting routes become available when NiceGUI starts

## User Interaction Logic
No direct interaction logic exists here.

## Current Limitations
- No central route manifest or metadata in package initializer.

## Existing Issues
- No direct file-level issues identified.
