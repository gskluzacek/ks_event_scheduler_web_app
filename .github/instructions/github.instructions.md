---
description: "Reference for .github repository automation assets, agent manifests, and governance files. Use when editing agent files, workflows, MCP config, or AI documentation controls."
applyTo: ".github/**"
---
# GitHub Configuration and Agent Ecosystem Reference

## Purpose
This file documents the repository's `.github/` contents, including agent manifests, instruction files, and automation-related expectations.

## Key Files
| File | Purpose |
|---|---|
| `.github/agents/repo-onboarder.agent.md` | Existing onboarder agent manifest |
| `.github/agents/KSP-sdlc.agent.md` | SDLC orchestrator for implementation workflows |
| `.github/agents/subagents/ksp-python.agent.md` | Stack specialist for Python/NiceGUI/FastAPI tasks |
| `.github/copilot-instructions.md` | Project-wide AI guidance |
| `.github/instructions/*.instructions.md` | Path-targeted instruction files loaded by Copilot |

## Workflows
| Workflow file | Trigger | Purpose |
|---|---|---|
| none | n/a | No GitHub Actions workflows are defined currently |

## Agent Manifests
| Agent name | File |
|---|---|
| `repo-onboarder` | `.github/agents/repo-onboarder.agent.md` |
| `KSP SDLC` | `.github/agents/KSP-sdlc.agent.md` |
| `KSP Python` | `.github/agents/subagents/ksp-python.agent.md` |

## Dependabot and Auto-Assign
- Dependabot: not configured (no `.github/dependabot.yml`).
- Auto-assign: not configured (no codeowners-driven assignment policy files in `.github/`).

## MCP Configuration
- No `.github/copilot-mcp.json` is configured because Jira/Confluence/Atlassian are not in use for this repository at this time.

## Notes for AI Agents
- Keep agent naming aligned with `KSP` prefix.
- Do not assume workflow automation exists; validate manually unless workflows are added later.
- Update this file whenever agents or automation files are added, removed, or renamed.

## Cross-References
- `.github/copilot-instructions.md`
- `.github/instructions/architecture.instructions.md`
- `.github/instructions/deprecated-features.instructions.md`

## Self-Healing
Agents reading this file must verify these claims before acting:
- Confirm listed agents exist under `.github/agents/`.
- Confirm listed workflows match `.github/workflows/` exactly.
- Confirm MCP status matches `.github/copilot-mcp.json` presence and intended usage.

If any mismatch is found, update this file first.
`<!-- Self-healed YYYY-MM-DD: [what changed and why] -->`
