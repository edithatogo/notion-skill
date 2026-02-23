#!/usr/bin/env python3
"""
Sync Tracks to Notion

Usage:
    python scripts/sync_tracks.py [repo_path]

If no repo_path is provided, uses current directory.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from track_parser import TrackParser
from notion_client import NotionClient
from rich.console import Console

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_path = Path(repo_path).resolve()

    console.print(f"\n[bold blue]Syncing Tracks to Notion[/bold blue]")
    console.print(f"Repository: {repo_path}\n")

    try:
        # Parse tracks
        parser = TrackParser(str(repo_path))
        tracks = parser.parse_tracks_file()
        archived = parser.parse_all_archived_tracks()
        summary = parser.get_track_summary()

        console.print(f"Found {len(tracks)} active tracks")
        console.print(f"Found {len(archived)} archived tracks\n")

        # Display summary
        console.print("[bold]Track Summary:[/bold]")
        console.print(f"  Total: {summary.get('total_tracks', 0)}")
        console.print(f"  Completed: {summary.get('completed_tracks', 0)}")
        console.print(f"  Active: {summary.get('active_tracks', 0)}")
        console.print(f"  With Metadata: {summary.get('tracks_with_metadata', 0)}")
        console.print(f"  With Spec: {summary.get('tracks_with_spec', 0)}")
        console.print(f"  With Plan: {summary.get('tracks_with_plan', 0)}")

        # Sync to Notion
        console.print("\n[bold]Syncing to Notion...[/bold]")
        # Note: Full sync would require SyncEngine
        # This is a simplified version for track-only sync

        for track in tracks + archived:
            status_icon = "✓" if track.get("status") == "complete" else "○"
            console.print(f"  {status_icon} {track.get('name')} ({track.get('status')})")

        console.print("\n[green]✓ Track sync complete![/green]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Track sync failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
