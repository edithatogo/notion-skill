#!/usr/bin/env python3
"""
Reflect Repository to Notion

Usage:
    python scripts/reflect_repo.py <repo_path>

Example:
    python scripts/reflect_repo.py C:\Users\60217257\repos\humanizer
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_engine import SyncEngine
from rich.console import Console
from rich.table import Table

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    if len(sys.argv) < 2:
        console.print("[red]Error:[/red] Repository path required")
        console.print("Usage: python reflect_repo.py <repo_path>")
        sys.exit(1)

    repo_path = sys.argv[1]

    if not Path(repo_path).exists():
        console.print(f"[red]Error:[/red] Repository not found: {repo_path}")
        sys.exit(1)

    console.print(f"\n[bold blue]Reflecting Repository to Notion[/bold blue]")
    console.print(f"Repository: {repo_path}\n")

    try:
        engine = SyncEngine()
        result = engine.sync_repository(repo_path)

        if result["success"]:
            console.print("\n[green]✓ Sync completed successfully![/green]\n")

            # Display summary
            summary = result.get("summary", {})
            table = Table(title="Sync Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            for key, value in summary.items():
                table.add_row(key.replace("_", " ").title(), str(value))

            console.print(table)

            # Display steps
            console.print("\n[bold]Sync Steps:[/bold]")
            for step in result.get("steps", []):
                status_icon = "✓" if step.get("status") == "complete" else "✗"
                console.print(f"  {status_icon} {step.get('name')}")

        else:
            console.print("\n[red]✗ Sync failed[/red]")
            for error in result.get("errors", []):
                console.print(f"  • {error}")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Sync failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
