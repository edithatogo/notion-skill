# Notion Skill

Reflect repositories into Notion and integrate them with Linear tracks. Built for AI agents to maintain unified project visibility across Git, Linear, and Notion.

## Why Notion Skill

Managing projects across multiple tools creates fragmentation:
- **Git** has commits and branches
- **Linear** has issues and projects
- **Notion** has documentation and databases

The Notion Skill bridges these tools by automatically reflecting repository structure, conductor tracks, and Linear project data into unified Notion databases for complete visibility.

## Features

- **🔄 Repository Reflection**: Automatically create Notion pages mirroring repository structure
- **📋 Track Sync**: Parse conductor/tracks.md and sync to Notion databases
- **🔗 Linear Integration**: Link repositories to Linear projects, sync issues and cycles
- **📊 Unified Dashboards**: View all repositories, tracks, and Linear projects in one place
- **⚡ Incremental Updates**: Sync changes on commit or manual trigger
- **🎯 Conductor Support**: Native integration with conductor track workflows

## Getting Started

### Prerequisites

- Notion API key (create integration at [notion.so/my-integrations](https://www.notion.so/my-integrations))
- Linear API key (generate at [linear.app/settings/api](https://linear.app/settings/api))
- Python 3.9+ for scripts
- Node.js 18+ for CLI tools

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/notion-skill.git
cd notion-skill

# Install dependencies
pip install -r requirements.txt
npm install (optional, for CLI tools)

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create `.env` file:

```bash
NOTION_API_KEY=notion_api_key_here
NOTION_REPOSITORIES_DB_ID=database_id_for_repositories
NOTION_TRACKS_DB_ID=database_id_for_tracks
NOTION_LINEAR_PROJECTS_DB_ID=database_id_for_linear_projects
LINEAR_API_KEY=linear_api_key_here
```

Create `.notion-sync.json` in repositories you want to sync:

```json
{
  "enabled": true,
  "linearProjectId": "d1f6b72c-d938-4581-bccf-1d259abb6363",
  "syncFrequency": "on-commit",
  "includeArchivedTracks": true
}
```

## Usage

### Reflect a Repository

```bash
# Using CLI
python scripts/reflect_repo.py C:\Users\60217257\repos\humanizer

# Using slash command (in AI agent)
/notion-reflect-repo C:\Users\60217257\repos\humanizer
```

### Sync Tracks

```bash
# From repository directory
cd C:\Users\60217257\repos\humanizer
python scripts/sync_tracks.py

# Or use slash command
/notion-sync-tracks
```

### Link Linear Project

```bash
# Manually link repository to Linear project
python scripts/link_linear.py --repo humanizer --project "Humanizer Skill Development"

# Or use slash command
/notion-link-linear humanizer "Humanizer Skill Development"
```

### Check Sync Status

```bash
python scripts/sync_status.py

# Output:
# Repository Sync Status
# ─────────────────────────────────────────
# ✓ humanizer              Synced 2026-02-23 14:30
# ✓ linear-history         Synced 2026-02-23 14:25
# ✓ knowledge-work-plugins Synced 2026-02-23 14:20
# ✗ conductor-next         Not synced
```

## Notion Database Structure

### Repositories Database

| Field | Type | Description |
|-------|------|-------------|
| Name | Title | Repository name |
| Description | Text | Repository description |
| Path | Text | Local or remote path |
| Primary Language | Select | Main programming language |
| Last Commit | Date | Most recent commit date |
| Last Commit Author | Person | Git author |
| Has Conductor | Checkbox | Whether conductor folder exists |
| Track Count | Number | Number of conductor tracks |
| Linear Project | Relation | Linked Linear project |
| Status | Select | Active, Archived, Complete |

### Tracks Database

| Field | Type | Description |
|-------|------|-------------|
| Track Name | Title | Track identifier |
| Repository | Relation | Parent repository |
| Status | Select | Complete, Active, Paused, Planning |
| Priority | Select | P0, P1, P2, P3 |
| Commit SHA | Text | Git commit hash |
| Completed Date | Date | Track completion date |
| Linear Issues | Relation | Linked Linear issues |
| Archive Path | URL | Path to archived track |
| Dependencies | Relation | Dependent tracks |

### Linear Projects Database

| Field | Type | Description |
|-------|------|-------------|
| Project Name | Title | Linear project name |
| Linear URL | URL | Direct link to Linear |
| Status | Select | Backlog, Active, Complete, Archived |
| Team | Select | Linear team |
| Issue Count | Number | Total issues |
| Completed Issues | Number | Completed issue count |
| Start Date | Date | Project start date |
| Target Date | Date | Target completion |
| Repository | Relation | Linked repository |
| Last Updated | Date | Last sync timestamp |

## Project Structure

```
notion-skill/
├── SKILL.md                    # Main skill definition
├── AGENTS.md                   # Agent manifest
├── README.md                   # This file
├── package.json                # Node.js dependencies (optional)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .notion-sync.json.example   # Sync config template
├── src/
│   ├── notion_client.py        # Notion API wrapper
│   ├── linear_client.py        # Linear API wrapper
│   ├── git_analyzer.py         # Git repository analysis
│   ├── track_parser.py         # Conductor track parser
│   ├── sync_engine.py          # Main sync orchestration
│   └── cli.py                  # Command-line interface
├── scripts/
│   ├── reflect_repo.py         # Repository reflection
│   ├── sync_tracks.py          # Track synchronization
│   ├── link_linear.py          # Linear project linking
│   ├── sync_status.py          # Status reporting
│   └── sync_adapters.py        # Adapter synchronization
├── adapters/
│   ├── qwen/
│   ├── copilot/
│   ├── vscode/
│   └── claude/
├── commands/
│   ├── notion_reflect_repo.md
│   ├── notion_sync_tracks.md
│   ├── notion_link_linear.md
│   └── notion_sync_status.md
└── tests/
    ├── test_track_parser.py
    ├── test_sync_engine.py
    └── test_notion_client.py
```

## Conductor Integration

The Notion Skill has native support for conductor track workflows:

### Track Detection

Automatically detects tracks from:
- `conductor/tracks.md` - Main track registry
- `conductor/tracks/archive/` - Completed tracks
- `conductor/tracks/active/` - Active tracks
- Git commit messages referencing tracks

### Track Status Mapping

| Conductor Status | Notion Status | Linear Status |
|------------------|---------------|---------------|
| `[x]` | Complete | Done |
| `[~]` | In Progress | In Progress |
| `[ ]` | Active | Todo |
| (none) | Planning | Backlog |

### Track Metadata

Extracts from `metadata.json`:
- Priority (P0-P3)
- Dependencies
- Artifacts
- Owner
- Completed date

## Linear Integration

### Project Matching

Automatic matching using:
1. **Name Similarity**: Repository name ≈ Linear project name
2. **Explicit Mapping**: `.linear-project` file in repo
3. **Track References**: Linear URLs in conductor tracks

### Issue Sync

For each matched Linear project:
- Fetch all issues with status, assignee, priority
- Map issues to tracks via branch names or commit messages
- Reflect cycle and milestone information
- Update Notion on issue changes

### Cycle Reflection

If team uses Linear cycles:
- Show current and past cycles
- Track completion velocity (tracks/cycle)
- Link cycles to repository milestones

## Automation

### Git Hooks

Set up automatic sync on commit:

```bash
# Add to .git/hooks/post-commit
#!/bin/bash
python scripts/sync_tracks.py --incremental
```

### Scheduled Sync

Use Windows Task Scheduler or cron:

```bash
# Sync all repositories every hour
0 * * * * cd C:\Users\60217257\repos\notion-skill && python scripts/sync_all.py
```

### Webhook Integration

For CI/CD integration:

```python
# GitHub Actions example
- name: Sync to Notion
  run: python scripts/sync_tracks.py --repo ${{ github.repository }}
  env:
    NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
```

## Troubleshooting

### Notion API Rate Limits

**Symptom**: `Rate limit exceeded` errors

**Solution**:
- Batch updates where possible
- Implement exponential backoff (built-in)
- Reduce sync frequency for inactive repos

### Linear Project Not Found

**Symptom**: `No matching Linear project found`

**Solution**:
- Check project name matches repo name
- Create `.linear-project` file with explicit ID
- Use `/notion-link-linear` command for manual mapping

### Track Parse Errors

**Symptom**: `Failed to parse track: <track-name>`

**Solution**:
- Verify conductor/tracks.md format
- Check track folder exists in archive
- Run `python scripts/validate_tracks.py` for diagnostics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Lint code
ruff check src/
black --check src/
```

## Related Projects

- **linear-history**: Maps repository history to Linear issues
- **knowledge-work-plugins**: Domain-specific plugins with track support
- **conductor-next**: Track execution and workflow management
- **humanizer**: AI writing pattern detection (example tracked repo)

## License

MIT

## Support

- **Documentation**: See `SKILL.md` for detailed skill instructions
- **Issues**: Report bugs on GitHub
- **Discussions**: Share use cases and best practices

---

*Last updated: 2026-02-23*
*Version: 1.0.0*
