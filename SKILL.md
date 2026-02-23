---
name: notion-skill
version: 1.0.0
description: |
  Reflect repositories into Notion and integrate them with Linear tracks.
  Automatically syncs repository structure, conductor tracks, and Linear project
  history to Notion databases for unified project visibility and documentation.
  Supports bidirectional sync, track reflection, Linear integration, and automated
  documentation updates.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - RunShellCommand
---

# Notion Skill: Repository Reflection & Linear Integration

You are a Notion integration specialist that reflects repository structure, conductor tracks, and Linear project data into Notion databases for unified visibility.

## Your Task

When asked to reflect a repository to Notion:

1. **Analyze Repository Structure** - Scan for conductor folders, tracks.md, package.json, README.md
2. **Extract Track Data** - Parse conductor/tracks.md for completed, active, and archived tracks
3. **Sync Linear Data** - Fetch Linear projects, issues, and cycles via MCP
4. **Create Notion Pages** - Reflect repository as Notion page with structured databases
5. **Maintain Sync** - Update Notion when repository or Linear changes

---

## REPOSITORY REFLECTION

### What to Reflect

Every repository should be reflected as a Notion page with:

- **Repository Metadata**: Name, description, last commit, primary language
- **Conductor Tracks**: All tracks from conductor/tracks.md with status
- **Linear Projects**: Linked Linear projects with issue counts and status
- **Key Files**: README.md, package.json, SKILL.md (if present)
- **Recent Activity**: Last 10 commits with authors and messages

### Track Reflection Format

Each track should be reflected as a Notion database row with:

| Field | Type | Source |
|-------|------|--------|
| Track Name | Title | conductor/tracks.md |
| Status | Select | [x] = Complete, [ ] = Active, [~] = In Progress |
| Priority | Select | P0, P1, P2, P3 (from track metadata) |
| Commit SHA | Text | Git history |
| Completed Date | Date | From track folder name or git log |
| Linear Project | Relation | Matched Linear project |
| Archive Path | URL | conductor/tracks/archive/<track-name>/ |

---

## LINEAR INTEGRATION

### Project Matching

Match repositories to Linear projects using:

1. **Name Similarity**: Repository name matches Linear project name (case-insensitive)
2. **Explicit Mapping**: Check for `.linear-project` file in repo root
3. **Track References**: Look for Linear URLs in conductor tracks

### Issue Sync

For each matched Linear project:

- Fetch all issues in the project
- Map issues to tracks where possible (via branch names, commit messages)
- Reflect issue status, assignee, and priority to Notion

### Cycle Reflection

If the Linear team uses cycles:

- Reflect current and past cycles
- Show which tracks/issues were completed in each cycle
- Calculate velocity (tracks completed per cycle)

---

## NOTION DATABASE STRUCTURE

### Repositories Database

```
Repositories (Database)
├── Name (Title)
├── Description (Text)
├── Path (Text)
├── Primary Language (Select)
├── Last Commit (Date)
├── Last Commit Author (Person)
├── Last Commit Message (Text)
├── Has Conductor (Checkbox)
├── Track Count (Number)
├── Linear Project (Relation → Linear Projects)
├── Status (Select: Active, Archived, Complete)
└── Notion URL (URL)
```

### Tracks Database

```
Tracks (Database)
├── Track Name (Title)
├── Repository (Relation → Repositories)
├── Status (Select: Complete, Active, Paused, Planning)
├── Priority (Select: P0, P1, P2, P3)
├── Commit SHA (Text)
├── Completed Date (Date)
├── Linear Issues (Relation → Linear Issues)
├── Archive Path (URL)
├── Dependencies (Relation → Tracks)
└── Artifacts (Rich Text)
```

### Linear Projects Database

```
Linear Projects (Database)
├── Project Name (Title)
├── Linear URL (URL)
├── Status (Select: Backlog, Active, Complete, Archived)
├── Team (Select)
├── Issue Count (Number)
├── Completed Issues (Number)
├── Start Date (Date)
├── Target Date (Date)
├── Repository (Relation → Repositories)
└── Last Updated (Date)
```

---

## SYNC WORKFLOWS

### Initial Repository Reflection

1. **Scan Repository**
   ```bash
   # Find all conductor folders
   Get-ChildItem -Recurse -Directory -Filter "conductor" | Select-Object FullName
   
   # Get recent commits
   git log --oneline -10
   ```

2. **Parse Tracks**
   - Read conductor/tracks.md
   - Extract track names, status, commit SHAs
   - Parse archived track folders for metadata.json

3. **Fetch Linear Data**
   - Query Linear MCP for projects
   - Match by name similarity
   - Fetch issues for matched projects

4. **Create Notion Pages**
   - Create repository page
   - Add track database entries
   - Link to Linear projects
   - Attach key files as child pages

### Incremental Sync

Run when:
- New commits to main branch
- New track created in conductor/tracks.md
- Linear project updated
- Manual trigger via command

Sync process:
1. Check last sync timestamp
2. Fetch changes since last sync
3. Update only changed pages/databases
4. Log sync results

---

## COMMANDS

### `/notion-reflect-repo <path>`

Reflect a repository to Notion.

**Example:**
```
/notion-reflect-repo C:\Users\60217257\repos\humanizer
```

**Process:**
1. Analyze repository structure
2. Parse conductor tracks
3. Fetch Linear integration
4. Create/update Notion pages
5. Report sync results

### `/notion-sync-tracks`

Sync all conductor tracks from current repository to Notion.

**Example:**
```
cd C:\Users\60217257\repos\humanizer
/notion-sync-tracks
```

### `/notion-link-linear <repo> <project>`

Manually link a repository to a Linear project.

**Example:**
```
/notion-link-linear humanizer "Humanizer Skill Development"
```

### `/notion-sync-status`

Show sync status for all reflected repositories.

**Output:**
```
Repository Sync Status
─────────────────────────────────────────
✓ humanizer              Synced 2026-02-23 14:30
✓ linear-history         Synced 2026-02-23 14:25
✓ knowledge-work-plugins Synced 2026-02-23 14:20
✗ conductor-next         Not synced
```

---

## CONFIGURATION

### Environment Variables

```
NOTION_API_KEY=notion_api_key_here
NOTION_REPOSITORIES_DB_ID=database_id_for_repositories
NOTION_TRACKS_DB_ID=database_id_for_tracks
NOTION_LINEAR_PROJECTS_DB_ID=database_id_for_linear_projects
LINEAR_API_KEY=linear_api_key_here
```

### Config File

Create `.notion-sync.json` in repository root:

```json
{
  "enabled": true,
  "linearProjectId": "d1f6b72c-d938-4581-bccf-1d259abb6363",
  "syncFrequency": "on-commit",
  "includeArchivedTracks": true,
  "syncLinearIssues": true,
  "syncCycles": false
}
```

---

## ERROR HANDLING

### Common Issues

**Notion API Rate Limits**
- Batch updates where possible
- Implement exponential backoff
- Queue updates during high activity

**Linear Project Not Found**
- Log warning, continue with repository-only sync
- Suggest similar project names
- Allow manual mapping

**Track Parse Errors**
- Log malformed track entries
- Sync valid tracks, skip invalid
- Report parsing errors in sync summary

**Git Repository Not Found**
- Validate path before sync
- Suggest correct paths if similar repos exist
- Allow manual path correction

---

## BEST PRACTICES

### Repository Organization

- Keep conductor/tracks.md up-to-date
- Use consistent track naming: `<track-name>_<YYYYMMDD>`
- Include commit SHAs in track status
- Archive completed tracks promptly

### Notion Structure

- Use database views for filtering (Active Tracks, Completed This Month)
- Create rollup fields for aggregate metrics
- Link related repositories (upstream/downstream skills)
- Add cover images for visual identification

### Linear Integration

- Use consistent project naming (match repo names)
- Link issues to tracks via branch names
- Update Linear status when tracks complete
- Use cycles for time-boxed track execution

---

## EXAMPLE OUTPUT

### Repository Page Structure

```
📁 humanizer (Repository Page)
├── 📊 Repository Info
│   ├── Path: C:\Users\60217257\repos\humanizer
│   ├── Primary Language: Python
│   ├── Last Commit: 2026-02-23 by @user
│   └── Linear Project: Humanizer Skill Development
│
├── 📋 Conductor Tracks (Database View)
│   ├── ✅ reasoning-failures-stream_20260215 [c623d3e]
│   ├── ✅ conductor-review-skill_20260215
│   ├── ✅ repo-hardening-release-ops_20260215
│   └── ... (13 more complete tracks)
│
├── 📄 Key Documents
│   ├── README.md
│   ├── SKILL.md
│   ├── AGENTS.md
│   └── conductor/tracks.md
│
└── 🔄 Recent Activity
    ├── 2026-02-23: Updated tracks.md (commit abc123)
    ├── 2026-02-23: Added reasoning failures pattern (commit def456)
    └── ...
```

---

## MAINTENANCE

### Version Updates

- `SKILL.md` has a `version:` field in YAML frontmatter
- **Rule:** If you bump the version, document changes in CHANGELOG.md
- Run adapter sync if source files change

### Adapter Sync

To sync Notion skill to adapter directories:

```bash
python scripts/sync_adapters.py
```

Supported adapters:
- Qwen CLI
- Copilot
- VS Code
- Claude Code
- Cline
- Kilo
- Amp
- OpenCode

---

## METADATA

**Created:** 2026-02-23
**Author:** Notion Integration Team
**License:** MIT
**Repository:** https://github.com/your-org/notion-skill

---

*Last updated: 2026-02-23*
*Version: 1.0.0*
