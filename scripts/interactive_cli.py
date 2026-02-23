#!/usr/bin/env python3
"""
Interactive CLI for Notion Skill

Enhanced command-line interface with rich prompts, progress bars, and interactive menus.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich library not available. Install with: pip install rich")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_engine import SyncEngine
from sync_metrics import MetricsCollector
from incremental_sync import IncrementalSyncManager

logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    console = Console()


def print_banner():
    """Print application banner."""
    if not RICH_AVAILABLE:
        print("Notion Skill CLI")
        print("=" * 50)
        return
    
    console.print(Panel.fit(
        "[bold blue]Notion Skill CLI[/bold blue]\n"
        "[dim]Repository Reflection & Linear Integration[/dim]",
        border_style="blue",
    ))


def interactive_sync(repo_path: Optional[str] = None):
    """
    Interactive repository sync with preview and confirmation.

    Args:
        repo_path: Optional repository path
    """
    if not RICH_AVAILABLE:
        print("Rich library required for interactive mode")
        return

    # Get repository path
    if not repo_path:
        repo_path = Prompt.ask(
            "[bold]Repository path[/bold]",
            default=".",
        )

    repo_path = Path(repo_path).resolve()

    if not repo_path.exists():
        console.print(f"[red]Error:[/red] Repository not found: {repo_path}")
        return

    if not (repo_path / ".git").exists():
        console.print(f"[yellow]Warning:[/yellow] {repo_path} does not appear to be a Git repository")
        if not Confirm.ask("Continue anyway?"):
            return

    console.print(f"\n[bold blue]Analyzing Repository[/bold blue]")
    console.print(f"Path: {repo_path}\n")

    # Initialize engine
    engine = SyncEngine()

    # Run in preview mode first
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("Analyzing repository...", total=None)
        result = engine.sync_repository(str(repo_path), preview=True)
        progress.update(task, completed=True)

    # Show preview
    if result.get("preview"):
        console.print("\n" + result["preview"])

    changes = result.get("changes_detected", {})
    if not changes.get("has_changes"):
        console.print("\n[green]✓ No changes detected. Sync not needed.[/green]")
        return

    # Confirm sync
    console.print()
    if not Confirm.ask("[bold]Proceed with sync?[/bold]"):
        console.print("[dim]Sync cancelled[/dim]")
        return

    # Choose sync mode
    sync_mode = Prompt.ask(
        "[bold]Sync mode[/bold]",
        choices=["incremental", "full", "force"],
        default="incremental",
    )

    # Execute sync
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("Syncing to Notion...", total=None)
        
        result = engine.sync_repository(
            str(repo_path),
            force=(sync_mode == "force"),
        )
        
        progress.update(task, completed=True)

    # Show results
    console.print()
    if result.get("success"):
        console.print("[bold green]✓ Sync completed successfully![/bold green]")
        
        summary = result.get("summary", {})
        table = Table(title="Sync Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in summary.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(table)
    else:
        console.print("[bold red]✗ Sync failed[/bold red]")
        for error in result.get("errors", []):
            console.print(f"  • {error}")


def show_sync_dashboard():
    """Display sync metrics dashboard."""
    if not RICH_AVAILABLE:
        print("Rich library required")
        return

    collector = MetricsCollector()
    summary = collector.get_summary(days=30)

    console.print("\n[bold blue]Sync Metrics Dashboard[/bold blue]")
    console.print("[dim]Last 30 days[/dim]\n")

    # Summary cards
    from rich.columns import Columns
    from rich.panel import Panel

    cards = []
    cards.append(Panel(f"[bold]{summary.get('total_syncs', 0)}[/bold]\n[dim]Total Syncs[/dim]", style="blue"))
    cards.append(Panel(f"[bold]{summary.get('successful_syncs', 0)}[/bold]\n[dim]Successful[/dim]", style="green"))
    cards.append(Panel(f"[bold]{summary.get('duration', {}).get('mean_ms', 0):.0f}ms[/bold]\n[dim]Avg Duration[/dim]", style="yellow"))
    cards.append(Panel(f"[bold]{summary.get('success_rate', {}).get('mean', 0):.1%}[/bold]\n[dim]Success Rate[/dim]", style="cyan"))

    console.print(Columns(cards))

    # Sync modes breakdown
    console.print("\n[bold]Sync Modes[/bold]")
    for mode, count in summary.get("sync_modes", {}).items():
        console.print(f"  • {mode.title()}: {count}")

    # Repository stats
    console.print("\n[bold]Top Repositories[/bold]")
    table = Table()
    table.add_column("Repository", style="cyan")
    table.add_column("Syncs", justify="right")
    table.add_column("Items", justify="right")
    table.add_column("Avg Duration", justify="right")

    # Would need to get actual repo stats here
    # For now, show placeholder
    table.add_row("humanizer", "15", "127", "1.2s")
    table.add_row("knowledge-work-plugins", "12", "89", "1.5s")
    table.add_row("linear-history", "8", "45", "0.9s")

    console.print(table)

    # Recent syncs
    console.print("\n[bold]Recent Syncs[/bold]")
    dashboard = collector.generate_dashboard_markdown()
    console.print(Markdown(dashboard))


def manage_workspaces():
    """Interactive workspace management."""
    if not RICH_AVAILABLE:
        print("Rich library required")
        return

    from multi_workspace import WorkspaceManager
    
    manager = WorkspaceManager()

    while True:
        console.print("\n[bold blue]Workspace Management[/bold blue]\n")

        # List workspaces
        workspaces = manager.list_workspaces()
        
        if not workspaces:
            console.print("[yellow]No workspaces configured[/yellow]")
        else:
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Workspace ID")
            table.add_column("Databases")
            table.add_column("Status")

            for ws in workspaces:
                status = "✓ Current" if ws["current"] else "Enabled" if ws["enabled"] else "Disabled"
                table.add_row(
                    ws["name"],
                    ws["workspace_id"],
                    str(ws["database_count"]),
                    status,
                )

            console.print(table)

        # Menu
        console.print()
        choice = Prompt.ask(
            "Action",
            choices=["select", "add", "remove", "export", "quit"],
            default="quit",
        )

        if choice == "select":
            name = Prompt.ask("Workspace name")
            if manager.select_workspace(name):
                console.print(f"[green]Selected workspace: {name}[/green]")
                manager.save_config()

        elif choice == "add":
            name = Prompt.ask("Workspace name")
            workspace_id = Prompt.ask("Workspace ID")
            api_key = Prompt.ask("API key", password=True)
            
            manager.add_workspace(
                name=name,
                api_key=api_key,
                workspace_id=workspace_id,
                databases={},
            )
            manager.save_config()
            console.print(f"[green]Added workspace: {name}[/green]")

        elif choice == "remove":
            name = Prompt.ask("Workspace name to remove")
            manager.remove_workspace(name)
            manager.save_config()

        elif choice == "export":
            output = Prompt.ask("Export file", default="workspaces-export.json")
            manager.export_config(output)

        elif choice == "quit":
            break


def main():
    """Main CLI entry point."""
    print_banner()

    if not RICH_AVAILABLE:
        print("\nInstall rich for interactive mode: pip install rich")
        print("\nBasic commands:")
        print("  sync <repo_path>  - Sync repository")
        print("  status            - Show sync status")
        print("  metrics           - Show metrics")
        return

    console.print()
    console.print("[bold]What would you like to do?[/bold]\n")

    choice = Prompt.ask(
        "Action",
        choices=[
            "sync - Sync repository to Notion",
            "dashboard - View sync metrics dashboard",
            "workspaces - Manage workspaces",
            "quit - Exit",
        ],
        default="quit",
    )

    if "sync" in choice:
        interactive_sync()
    elif "dashboard" in choice:
        show_sync_dashboard()
    elif "workspaces" in choice:
        manage_workspaces()
    elif "quit" in choice:
        console.print("\n[dim]Goodbye![/dim]\n")
        return

    # Return to menu
    main()


if __name__ == "__main__":
    main()
