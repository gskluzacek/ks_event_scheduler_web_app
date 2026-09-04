# app/components/__init__.py

## Purpose
Marks `app.components` as a package for shared UI building blocks.

## NiceGUI and Web Feature Relevance
This package groups reusable NiceGUI composition helpers used across multiple pages:
- shared layout frame
- role switcher header controls
- timezone cascading selector

No direct `ui.*` code exists in this file, but it enables clean imports that keep page modules readable.

## User Interaction Logic
No direct interaction handling occurs in this file.

## Current Limitations
- Empty package initializer; no explicit public API export surface.

## Existing Issues
- No direct issues found.
