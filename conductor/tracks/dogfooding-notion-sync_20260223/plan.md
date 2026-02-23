# Plan: Dogfooding Notion Sync

**Track**: dogfooding-notion-sync_20260223  
**Status**: planning  

---

## Tasks

### 1. Prerequisites Check [PENDING]

- [ ] Verify all improvement modules are complete
- [ ] Ensure Notion API key is configured
- [ ] Ensure Linear API key is configured

### 2. Create Notion Databases [PENDING]

- [ ] Create Repositories database from template
- [ ] Create Tracks database from template
- [ ] Create Linear Projects database from template
- [ ] Create Sync Metrics database from template

### 3. Configure Sync [PENDING]

- [ ] Create `.notion-sync.json` with Linear project ID
- [ ] Set database IDs in environment or config
- [ ] Test Notion connection

### 4. Run Initial Sync [PENDING]

- [ ] Execute: `python scripts/reflect_repo.py .`
- [ ] Verify repository page created
- [ ] Verify tracks synced (expect ~15 tracks)
- [ ] Verify Linear project linked

### 5. Test Incremental Sync [PENDING]

- [ ] Make small change to conductor/tracks.md
- [ ] Run: `python scripts/reflect_repo.py . --preview`
- [ ] Verify change detected
- [ ] Execute sync
- [ ] Verify only changes synced

### 6. Validate Metrics [PENDING]

- [ ] Check metrics recorded
- [ ] Generate dashboard: `python scripts/show_metrics.py`
- [ ] Verify sync count, duration, success rate

### 7. Document Findings [PENDING]

- [ ] Note any errors or issues
- [ ] Document workarounds
- [ ] Update documentation if needed
- [ ] Create bug issues for any problems found

---

## Verification Checklist

- [ ] Notion Repositories database shows notion-skill
- [ ] Notion Tracks database shows all conductor tracks
- [ ] Linear project is linked
- [ ] Sync completed without errors
- [ ] Metrics show successful sync
- [ ] Incremental sync detects changes correctly

---

## Commands

```bash
# Initial sync
python scripts/reflect_repo.py C:\Users\60217257\repos\notion-skill

# Preview mode
python scripts/reflect_repo.py . --preview

# Show metrics
python -c "from src.sync_metrics import MetricsCollector; c = MetricsCollector(); print(c.generate_dashboard_markdown())"

# Interactive mode
python scripts/interactive_cli.py
```

---

*Plan created: 2026-02-23*
