#!/usr/bin/env python3
"""
Show Sync Status for Repositories

Usage:
    python scripts/sync_status.py [repo_paths...]

If no repo_paths provided, scans common repos directory.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()


def get_sync_status(repo_path: Path) -> dict:
    """Get sync status for a repository."""
    config_file = repo_path / ".notion-sync.json"
    
    status = {
        "name": repo_path.name,
        "path": str(repo_path),
        "configured": False,
        "last_sync": "Never",
        "sync_status": "Not synced",
        "linear_project": None,
        "track_count": 0,
    }
    
    if config_file.exists():
        status["configured"] = True
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                status["linear_project"] = config.get("linearProjectId")
                
                # Check for last sync timestamp (would be stored by sync process)
                if os.path.exists(repo_path / ".last-sync.json"):
                    with open(repo_path / ".last-sync.json", "r") as sf:
                        sync_data = json.load(sf)
                        status["last_sync"] = sync_data.get("timestamp", "Unknown")
                        status["sync_status"] = "Synced"
        except Exception:
            pass
    
    # Count tracks if conductor exists
    conductor_tracks = repo_path / "conductor" / "tracks.md"
    if conductor_tracks.exists():
        try:
            content = conductor_tracks.read_text()
            # Rough count of tracks
            status["track_count"] = content.count("[x]") + content.count("[~]") + content.count("[ ]")
        except Exception:
            pass
    
    return status


def main():
    console.print("\n[bold blue]Repository Sync Status[/bold blue]\n")
    
    # Determine which repos to check
    if len(sys.argv) > 1:
        repo_paths = [Path(p).resolve() for p in sys.argv[1:]]
    else:
        # Default: scan repos directory
        base_dir = Path(__file__).parent.parent.parent
        repo_paths = [
            d for d in base_dir.iterdir()
            if d.is_dir() and (d / ".git").exists()
        ]
    
    if not repo_paths:
        console.print("[yellow]No repositories found[/yellow]")
        return
    
    # Get status for each repo
    statuses = [get_sync_status(p) for p in repo_paths]
    
    # Create table
    table = Table(title=f"Sync Status for {len(statuses)} Repositories")
    table.add_column("Repository", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Last Sync", style="yellow")
    table.add_column("Tracks", style="blue")
    table.add_column("Linear", style="magenta")
    
    for status in statuses:
        status_icon = "✓" if status["sync_status"] == "Synced" else "✗"
        table.add_row(
            status["name"],
            f"{status_icon} {status['sync_status']}",
            status["last_sync"],
            str(status["track_count"]),
            "Linked" if status["linear_project"] else "Not linked",
        )
    
    console.print(table)
    
    # Summary
    synced = sum(1 for s in statuses if s["sync_status"] == "Synced")
    console.print(f"\n[bold]Summary:[/bold] {synced}/{len(statuses)} repositories synced")


if __name__ == "__main__":
    main()
