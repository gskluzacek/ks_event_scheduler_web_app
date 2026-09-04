# Copilot Instructions for kingshot-scheduler

## Project Overview
kingshot-scheduler is a Python/NiceGUI web application for planning and scheduling Kingshot alliance events. Primary consumers are Kingshot users and alliance admins who need to register accounts, manage players, track availability time slots, and coordinate event windows.

## Documentation Maintenance
| Trigger | Update required |
|---|---|
| New top-level folder or major module change | Add/update the matching `.github/instructions/[folder].instructions.md` |
| New build/test/run command | Update this file: Development Commands |
| New/changed workflow under `.github/` | Update `.github/instructions/github.instructions.md` |
| New agent or changed agent role | Update this file: AI Agents and `.github/instructions/github.instructions.md` |
| New deprecated pattern or retired module | Update `.github/instructions/deprecated-features.instructions.md` |
| New env var or secret | Update this file: Key Configuration |

## Application Name(s)
| Variant | Source |
|---|---|
| kingshot-scheduler | `pyproject.toml` project name |
| Kingshot Event Scheduling Web Application | `pyproject.toml` description and `documentation/web_app_requirements.md` |
| Kingshot Scheduler | UI titles in `app/main.py` and page modules |

## Repository Structure
| Top-level path | Purpose | Instruction file |
|---|---|---|
| `app/` | Main NiceGUI application package (pages, auth, models, utilities). | `.github/instructions/app.instructions.md` |
| `documentation/` | Product requirements, design notes, TODOs, and implementation context. | `.github/instructions/documentation.instructions.md` |
| `nicegui_exploration/` | Standalone experiments for NiceGUI concepts and patterns. | `.github/instructions/nicegui_exploration.instructions.md` |
| `discord_integration_poc/` | OAuth and guild-membership proof-of-concept scripts. | `.github/instructions/discord_integration_poc.instructions.md` |
| `ai_authored_content/` | Archived AI-generated patch artifacts and prior iterations. | `.github/instructions/ai_authored_content.instructions.md` |
| `assets/` | Static assets used by demos and UI mocks. | `.github/instructions/assets.instructions.md` |
| `.github/` | Agent manifests and repository AI-instructions ecosystem. | `.github/instructions/github.instructions.md` |

## Tech Stack
| Layer | Technology | Version/source |
|---|---|---|
| Runtime language | Python | `>=3.14` from `pyproject.toml` |
| UI framework | NiceGUI | `>=3.16.0` from `pyproject.toml` |
| API framework | FastAPI | `>=0.141.1` from `pyproject.toml` |
| HTTP client | httpx | `>=0.28.1` from `pyproject.toml` |
| Date/time helpers | python-dateutil | `>=2.9.0` from `pyproject.toml` |
| Env management | python-dotenv | `>=1.2.3` from `pyproject.toml` |
| Packaging/tooling | uv / pyproject | `pyproject.toml`, `uv.lock` |

## Development Commands
```bash
# Install/sync dependencies
uv sync

# Prepare local environment
cp .env.example .env

# Run app from repository root
uv run python -m app.main

# Optional direct python invocation (if uv not used)
python -m app.main
```

Notes:
- No first-class automated test command is currently defined in repository manifests.
- If tests are added, document canonical commands here and in stack instruction files.

## CI/CD Pipeline
Current state: no `.github/workflows/` files are present and no Jenkinsfile is present. CI/CD is not configured in-repo yet.

| Workflow | Trigger | Purpose |
|---|---|---|
| none | n/a | CI/CD workflows have not been created yet |

## AI Agents
| Agent | Role | Invocation |
|---|---|---|
| `repo-onboarder` | Generates/refreshes this repository's AI instruction ecosystem. | Direct user invocation |
| `KSP SDLC` | End-to-end implementation orchestrator in Normal mode for this repo. | Direct user invocation |
| `KSP Python` | Python/NiceGUI/FastAPI stack implementation specialist. | Called by `KSP SDLC` or directly by advanced users |

Required secrets and environment context for coding tasks:
- Discord integration values in `.env`: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_BOT_TOKEN`, `DISCORD_REDIRECT_URI`, `STORAGE_SECRET`.
- Atlassian/Jira/Confluence secrets are currently not used in this repository.

MCP endpoint summary:
- No Atlassian MCP endpoint is configured or required at this time.

SDLC development mode note:
- `KSP SDLC` is configured in **Normal mode** (production code first, tests added afterward) and enforces test completion before push.

## Testing Strategy
- Automated tests are not yet established in this repository.
- Existing quality checks are manual via local run-through of pages and role-based flows.
- When tests are introduced, place them under a dedicated `tests/` tree with unit vs integration separation.
- Prioritize tests for:
  - page-level filter behavior in `app/pages/*.py`
  - auth callback and state handling in `app/pages/auth.py`
  - guild verification outcome handling in `app/auth/discord_guild.py`

## Key Configuration
| Category | Location | Notes |
|---|---|---|
| Python project metadata | `pyproject.toml` | Canonical dependency and version definitions |
| Locked dependency graph | `uv.lock` | Reproducible dependency state |
| Runtime env template | `.env.example` | Copy to `.env` for local runs |
| Git ignore and generated-artifact policy | `.gitignore` | Includes `.env`, `.venv`, `.nicegui`, caches |

## Confluence and Jira Integration
- Confluence: not configured.
- Jira: not configured.
- Team JQL filters: not applicable.
- If introduced later, create `.github/instructions/jira.instructions.md`, `.github/instructions/confluence.instructions.md`, and corresponding utility agents.

## UI Design Standards
- Prefer Python-first NiceGUI patterns over ad hoc JavaScript.
- Use shared layout scaffolding through `app/components/layout.py` for header/nav consistency.
- Keep role-gated behavior explicit and centralized through `app/components/role_switcher.py`.
- Keep table filters and sort persistence through utilities in `app/utils/filters.py`.
- Use readable labels and concise helper text; avoid burying validation state.

## External Repository Interface Points
Current state: none identified.

| External repository | Interface type | Internal consumer |
|---|---|---|
| none | n/a | n/a |

## Deprecated Code
- Reference `.github/instructions/deprecated-features.instructions.md` for historical/legacy areas and migration notes.

## Cross-Cutting Constraints
- Do not store real secrets in source-controlled files.
- Keep OAuth callback state validation intact for CSRF protection.
- Treat Discord API/network errors as user-visible failures, not silent passes.
- Respect NiceGUI state-scope rules: avoid cross-user leakage via module globals unless intentionally mock-only.
- Keep repository documentation in sync with code and manifests when making structural changes.

## Documentation Gaps
- No Jira board, Confluence space, or Atlassian MCP integration is currently available; no external operational docs were ingested.
- No in-repo CI workflows currently exist.
- Automated test harness and standards are not fully documented yet.
- Module-level documentation is sparse outside inline comments and a few markdown files.

## Self-Healing Protocol
All AI agents working in this repository must run Self-Healing probes on every instruction file they load before implementation. If a version, path, command, workflow, or agent reference is stale, the agent must update the affected instruction file immediately and report the correction to the user. Self-healing edits must use this commit convention: `docs(instructions): self-heal [filename] - [reason]`.
