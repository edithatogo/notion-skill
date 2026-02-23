---
adapter_metadata:
  skill_name: notion-skill
  skill_version: 1.0.0
  last_synced: 2026-02-23
  source_path: SKILL.md
  adapter_id: codex-cli
  adapter_format: AGENTS.md
---

# Notion Skill (agents manifest)

This repository defines the **Notion Skill**, designed to reflect repositories into Notion and integrate them with Linear tracks for unified project visibility.

## Capability

The Notion skill provides automated synchronization between:
- **Git Repositories**: Structure, conductor tracks, commit history
- **Linear**: Projects, issues, cycles, milestones
- **Notion**: Databases for repositories, tracks, and Linear integration

### Core Workflows

- **Repository Reflection**: Create Notion pages mirroring repository structure
- **Track Sync**: Parse conductor/tracks.md and reflect to Notion databases
- **Linear Integration**: Link repositories to Linear projects, sync issues
- **Incremental Updates**: Sync changes on commit or manual trigger

Primary prompt: [SKILL.md](SKILL.md). Supported adapters live in the `adapters/` directory.

## Context

This file serves as the **Agents.md** standard manifest for this repository. It provides guidance for AI agents to understand how to interact with this codebase.

### Repository structure

- `src/`
  - Modular components for Notion, Linear, and Git integration
- `SKILL.md`
  - Compiled skill file with full instructions
- `adapters/`
  - Tool-specific implementations (VS Code, Qwen, Copilot, etc.)
- `scripts/`
  - Automation for syncing and repository reflection
- `commands/`
  - Slash commands: `/notion-reflect-repo`, `/notion-sync-tracks`, `/notion-link-linear`

### Core instructions

You are the Notion integration specialist. Follow the workflows defined in `SKILL.md`.

When asked to reflect a repository:

1. Analyze repository structure (conductor folders, tracks.md, key files)
2. Parse conductor tracks with status, commits, and metadata
3. Fetch Linear project data via MCP
4. Create/update Notion pages and database entries
5. Report sync results with any errors or warnings

## Maintenance

To sync this skill to adapter directories:

```bash
python scripts/sync_adapters.py
```

### Making changes safely

- `SKILL.md` has a `version:` field in YAML frontmatter
- **Rule:** If you bump the version, update source in `src/` and run sync
- Test with a small repository before bulk reflection

## Interoperability

Check for specialized adapters in the `adapters/` directory for specific tool support (Antigravity, VS Code, Gemini, Qwen, Copilot, Cline, Kilo, Amp, OpenCode).

## Related Skills

- **linear-history**: Maps repository history to Linear issues
- **knowledge-work-plugins**: Domain-specific plugins including product-management tracks
- **conductor-next**: Track execution and workflow management
