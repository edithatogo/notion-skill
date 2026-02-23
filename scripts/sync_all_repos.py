#!/usr/bin/env python3
"""
Sync All Conductor Repos

Script to sync all repositories with conductor folders to Notion and Linear.
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set environment for imports
os.environ['PYTHONPATH'] = str(src_path)

from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))

# Now import from src
from sync_engine import SyncEngine
from rich.console import Console
from rich.table import Table

console = Console()

# Repos with conductor folders
REPOS = [
    "conductor-next",
    "humanizer",
    "knowledge-work-plugins",
    "linear-history",
    "email-migration-validation",
    "outlook-organiser",
    "congenital-syphilis-economic-evaluation",
]

BASE_PATH = Path(r"C:\Users\60217257\repos")


def main():
    console.print("\n[bold blue]Syncing All Conductor Repos to Notion & Linear[/bold blue]\n")
    
    # Initialize engine
    try:
        engine = SyncEngine()
        console.print("[green]✓ Sync engine initialized[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize: {e}[/red]")
        console.print("\n[dim]Make sure you have run scripts/setup_wizard.py first[/dim]\n")
        return
    
    results = []
    
    for repo_name in REPOS:
        repo_path = BASE_PATH / repo_name
        
        if not repo_path.exists():
            console.print(f"[yellow]⚠ Skipping {repo_name}: Not found[/yellow]")
            results.append({"repo": repo_name, "status": "skipped", "reason": "not found"})
            continue
        
        if not (repo_path / ".git").exists():
            console.print(f"[yellow]⚠ Skipping {repo_name}: Not a git repo[/yellow]")
            results.append({"repo": repo_name, "status": "skipped", "reason": "not git repo"})
            continue
        
        console.print(f"\n[bold]Syncing {repo_name}...[/bold]")
        
        try:
            result = engine.sync_repository(
                str(repo_path),
                force=False,  # Use incremental sync
                preview=False,
            )
            
            if result.get("success"):
                summary = result.get("summary", {})
                changes = result.get("changes_detected", {})
                
                console.print(f"  [green]✓ Success[/green]")
                if changes:
                    console.print(f"    Changes: {changes.get('summary', 'N/A')}")
                console.print(f"    Mode: {summary.get('sync_mode', 'N/A')}")
                
                results.append({
                    "repo": repo_name,
                    "status": "success",
                    "mode": summary.get("sync_mode"),
                    "changes": changes.get("summary", "N/A"),
                })
            else:
                errors = result.get("errors", [])
                console.print(f"  [red]✗ Failed[/red]")
                for error in errors:
                    console.print(f"    • {error}")
                
                results.append({
                    "repo": repo_name,
                    "status": "failed",
                    "errors": errors,
                })
        
        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            results.append({
                "repo": repo_name,
                "status": "error",
                "error": str(e),
            })
    
    # Summary table
    console.print("\n[bold]Sync Summary[/bold]\n")
    
    table = Table()
    table.add_column("Repository", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    for result in results:
        status_icon = "✓" if result["status"] == "success" else "✗" if result["status"] in ["failed", "error"] else "○"
        status_text = result["status"].title()
        
        details = ""
        if result["status"] == "success":
            details = f"{result.get('mode', '')} - {result.get('changes', '')}"
        elif result["status"] in ["failed", "error"]:
            details = result.get("error", result.get("errors", ["Unknown"])[0] if isinstance(result.get("errors"), list) else "N/A")
        else:
            details = result.get("reason", "")
        
        table.add_row(f"{status_icon} {result['repo']}", status_text, details[:50] + "..." if len(details) > 50 else details)
    
    console.print(table)
    
    # Stats
    success_count = sum(1 for r in results if r["status"] == "success")
    console.print(f"\n[bold]Results: {success_count}/{len(REPOS)} repos synced successfully[/bold]\n")


if __name__ == "__main__":
    main()
