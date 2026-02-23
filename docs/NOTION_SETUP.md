# Notion Setup Guide

This guide will help you set up the Notion databases for the Notion Skill integration.

## Quick Setup (Recommended)

### Option 1: Use the Interactive CLI

```bash
cd notion-skill
python scripts/interactive_cli.py
```

Select "workspaces" to configure your Notion connection, then the CLI will guide you through database creation.

### Option 2: Manual Setup

1. **Create a new Notion page** called "Notion Skill Hub"

2. **Create four databases** using the templates in `src/notion_templates.py`:

   ### Repositories Database
   - Type: Table (Inline or Full Page)
   - Properties:
     - Name (Title)
     - Description (Text)
     - Path (Text)
     - Primary Language (Select)
     - Last Commit (Date)
     - Last Commit Author (Text)
     - Has Conductor (Checkbox)
     - Track Count (Number)
     - Linear Project (Relation)
     - Status (Select: Active, At Risk, Blocked, Archived, Complete)
     - Priority (Select: P0, P1, P2, P3)
     - Last Synced (Date)

   ### Tracks Database
   - Type: Table (Inline or Full Page)
   - Properties:
     - Track Name (Title)
     - Repository (Relation)
     - Status (Select: Planning, Active, In Progress, Review, Complete, Archived, Blocked)
     - Priority (Select: P0, P1, P2, P3)
     - Phase (Number)
     - Commit SHA (Text)
     - Completed Date (Date)
     - Linear Issues (Relation)
     - Archive Path (URL)
     - Dependencies (Relation)
     - Owner (Person)

   ### Linear Projects Database
   - Type: Table (Inline or Full Page)
   - Properties:
     - Project Name (Title)
     - Linear URL (URL)
     - Status (Select: Backlog, Active, At Risk, Complete, Archived)
     - Team (Select)
     - Issue Count (Number)
     - Completed Issues (Number)
     - Start Date (Date)
     - Target Date (Date)
     - Repository (Relation)
     - Last Updated (Last Edited Time)

   ### Sync Metrics Database
   - Type: Table (Inline or Full Page)
   - Properties:
     - Sync ID (Title)
     - Repository (Relation)
     - Timestamp (Date)
     - Duration (ms) (Number)
     - Items Synced (Number)
     - API Calls Made (Number)
     - Rate Limit Hits (Number)
     - Errors Count (Number)
     - Success Rate (Number, format: Percent)
     - Sync Mode (Select: Full, Incremental, Preview)

3. **Get Database IDs**
   - Open each database in Notion
   - Copy the database ID from the URL:
     - URL format: `https://www.notion.so/your-workspace/DATABASE_ID?v=...`
     - The ID is the part after the last slash before `?v=`

4. **Configure Environment Variables**

Create a `.env` file in the project root:

```bash
# Notion Configuration
NOTION_API_KEY=your_notion_integration_token
NOTION_REPOSITORIES_DB_ID=your_repositories_database_id
NOTION_TRACKS_DB_ID=your_tracks_database_id
NOTION_LINEAR_PROJECTS_DB_ID=your_linear_projects_database_id
NOTION_SYNC_METRICS_DB_ID=your_sync_metrics_database_id

# Linear Configuration
LINEAR_API_KEY=your_linear_api_key
LINEAR_TEAM_ID=2a6da0ae-f567-4af9-b507-18b962e861f8

# Optional: Webhook Configuration
LINEAR_WEBHOOK_SECRET=your_webhook_secret
NOTION_VERIFICATION_TOKEN=your_verification_token
```

## Getting Your Notion API Key

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "+ New integration"
3. Fill in the details:
   - Name: Notion Skill
   - Logo: (optional)
   - Associated workspace: Select your workspace
4. Click "Submit"
5. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`

## Connecting Notion Integration to Your Databases

1. After creating the integration, go to your Notion workspace
2. Click "..." (three dots) in the top right corner
3. Click "Connect to"
4. Select your "Notion Skill" integration
5. Repeat for each database you created

## Getting Your Linear API Key

1. Go to [linear.app/settings/api](https://linear.app/settings/api)
2. Click "New API Key"
3. Copy the key - this is your `LINEAR_API_KEY`

## Verifying Your Setup

Run the following command to test your configuration:

```bash
python -c "
from src import SyncEngine
from dotenv import load_dotenv
load_dotenv()

engine = SyncEngine()
print('✓ Configuration loaded successfully')
print(f'  Notion configured: {engine.notion is not None}')
print(f'  Linear configured: {engine.linear is not None}')
"
```

## Running the Dogfooding Track

Once everything is configured, run the dogfooding track to validate:

```bash
# Preview mode first
python scripts/reflect_repo.py . --preview

# Then actual sync
python scripts/reflect_repo.py .
```

## Troubleshooting

### "Database ID not found"
- Make sure you copied the full database ID (32 characters, with dashes)
- Verify the integration has access to the database

### "API rate limit exceeded"
- Wait a few seconds and try again
- The sync engine has automatic retry with backoff

### "No changes detected"
- This is normal if nothing changed since last sync
- Use `--force` flag to force a full sync

### "Linear project not found"
- Ensure the Linear project exists: https://linear.app/edithatogo/project/notion-skill-f8053ab4d1b9
- Check that your API key has access to the project

## Next Steps

After setup is complete:

1. **Run initial sync**: `python scripts/reflect_repo.py .`
2. **View dashboard**: `python scripts/interactive_cli.py` → Dashboard
3. **Set up webhooks** (optional): See `docs/WEBHOOK_SETUP.md`
4. **Enable MCP server** (optional): `python -m src.mcp_server`

---

For more help, see:
- `docs/COMPLETE_IMPLEMENTATION.md` - Full implementation guide
- `docs/IMPROVEMENTS_SUMMARY.md` - Feature documentation
- GitHub Issues: https://github.com/edithatogo/notion-skill/issues
