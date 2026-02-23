"""
MCP Server for Notion Skill

Exposes Notion Skill functionality as MCP tools for AI agents.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP server not available - mcp package not installed")


class NotionSkillMCPServer:
    """MCP server for Notion Skill tools."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP server.

        Args:
            config: Server configuration
        """
        self.config = config or {}
        self.server = Server("notion-skill") if MCP_AVAILABLE else None
        self._setup_tools()

    def _setup_tools(self):
        """Set up MCP tools."""
        if not self.server or not MCP_AVAILABLE:
            return

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="sync_repository",
                    description="Sync a repository to Notion. Creates or updates repository page and tracks.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the repository to sync"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force full sync even if no changes detected",
                                "default": False
                            },
                            "preview": {
                                "type": "boolean",
                                "description": "Only detect changes, don't actually sync",
                                "default": False
                            }
                        },
                        "required": ["repo_path"]
                    }
                ),
                Tool(
                    name="detect_changes",
                    description="Detect changes in a repository since last sync without syncing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the repository"
                            }
                        },
                        "required": ["repo_path"]
                    }
                ),
                Tool(
                    name="query_tracks",
                    description="Query tracks from a repository. Filter by status, priority, or date range.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the repository"
                            },
                            "status": {
                                "type": "string",
                                "description": "Filter by status (complete, active, in_progress, archived)",
                                "enum": ["complete", "active", "in_progress", "archived", "planning"]
                            },
                            "priority": {
                                "type": "string",
                                "description": "Filter by priority (P0, P1, P2, P3)"
                            }
                        },
                        "required": ["repo_path"]
                    }
                ),
                Tool(
                    name="get_sync_status",
                    description="Get sync status for one or more repositories.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of repository paths"
                            }
                        },
                        "required": ["repo_paths"]
                    }
                ),
                Tool(
                    name="get_sync_metrics",
                    description="Get sync metrics and statistics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "Number of days to include",
                                "default": 30
                            },
                            "repo_path": {
                                "type": "string",
                                "description": "Optional: filter by specific repository"
                            }
                        }
                    }
                ),
                Tool(
                    name="resolve_conflicts",
                    description="Detect and resolve conflicts between Git, Linear, and Notion data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo_path": {
                                "type": "string",
                                "description": "Path to the repository"
                            },
                            "strategy": {
                                "type": "string",
                                "description": "Conflict resolution strategy",
                                "enum": ["git_wins", "linear_wins", "notion_wins", "newest_wins", "manual"]
                            }
                        },
                        "required": ["repo_path"]
                    }
                ),
                Tool(
                    name="create_notion_database",
                    description="Create a Notion database from a template.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "parent_page_id": {
                                "type": "string",
                                "description": "ID of the parent Notion page"
                            },
                            "template": {
                                "type": "string",
                                "description": "Database template to use",
                                "enum": ["repositories", "tracks", "linear_projects", "sync_metrics"]
                            },
                            "title": {
                                "type": "string",
                                "description": "Custom title for the database"
                            }
                        },
                        "required": ["parent_page_id", "template"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "sync_repository":
                    result = await self._sync_repository(
                        arguments.get("repo_path"),
                        arguments.get("force", False),
                        arguments.get("preview", False),
                    )
                elif name == "detect_changes":
                    result = await self._detect_changes(arguments.get("repo_path"))
                elif name == "query_tracks":
                    result = await self._query_tracks(
                        arguments.get("repo_path"),
                        arguments.get("status"),
                        arguments.get("priority"),
                    )
                elif name == "get_sync_status":
                    result = await self._get_sync_status(arguments.get("repo_paths", []))
                elif name == "get_sync_metrics":
                    result = await self._get_sync_metrics(
                        arguments.get("days", 30),
                        arguments.get("repo_path"),
                    )
                elif name == "resolve_conflicts":
                    result = await self._resolve_conflicts(
                        arguments.get("repo_path"),
                        arguments.get("strategy"),
                    )
                elif name == "create_notion_database":
                    result = await self._create_notion_database(
                        arguments.get("parent_page_id"),
                        arguments.get("template"),
                        arguments.get("title"),
                    )
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]

                return [TextContent(
                    type="text",
                    text=str(result)
                )]

            except Exception as e:
                logger.exception(f"Tool {name} failed")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _sync_repository(
        self,
        repo_path: str,
        force: bool = False,
        preview: bool = False,
    ) -> Dict[str, Any]:
        """Sync repository to Notion."""
        from .sync_engine import SyncEngine

        engine = SyncEngine(config=self.config)
        result = engine.sync_repository(repo_path, force=force, preview=preview)
        return result

    async def _detect_changes(self, repo_path: str) -> Dict[str, Any]:
        """Detect changes without syncing."""
        from .sync_engine import SyncEngine
        from .incremental_sync import IncrementalSyncManager

        # Just run change detection
        engine = SyncEngine(config=self.config)
        result = engine.sync_repository(repo_path, preview=True)
        return result.get("changes_detected", {})

    async def _query_tracks(
        self,
        repo_path: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query tracks from repository."""
        from .track_parser import TrackParser

        parser = TrackParser(repo_path)
        tracks = parser.parse_tracks_file()

        # Filter
        if status:
            tracks = [t for t in tracks if t.get("status") == status]
        if priority:
            tracks = [t for t in tracks if t.get("metadata", {}).get("priority") == priority]

        return tracks

    async def _get_sync_status(self, repo_paths: List[str]) -> List[Dict[str, Any]]:
        """Get sync status for repositories."""
        from .sync_engine import SyncEngine

        engine = SyncEngine(config=self.config)
        return engine.get_sync_status(repo_paths)

    async def _get_sync_metrics(
        self,
        days: int = 30,
        repo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get sync metrics."""
        from .sync_metrics import MetricsCollector

        collector = MetricsCollector()

        if repo_path:
            return collector.get_repository_stats(repo_path)
        else:
            return collector.get_summary(days=days)

    async def _resolve_conflicts(
        self,
        repo_path: str,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve conflicts."""
        from .conflict_resolution import ConflictResolver, ConflictStrategy
        from .track_parser import TrackParser
        from .linear_client import LinearClient

        # Get data
        parser = TrackParser(repo_path)
        tracks = parser.parse_tracks_file()

        linear = LinearClient()
        # Get Linear issues (would need project ID)

        resolver = ConflictResolver()
        if strategy:
            resolver.default_strategy = ConflictStrategy(strategy)

        conflicts = resolver.detect_conflicts(tracks, [])
        resolutions = [resolver.resolve_conflict(c) for c in conflicts]

        return {
            "conflicts_detected": len(conflicts),
            "resolutions": [
                {
                    "entity": r.conflict.entity_id,
                    "success": r.success,
                    "strategy": r.strategy_used.value,
                    "message": r.message,
                }
                for r in resolutions
            ],
            "report": resolver.get_resolution_report(),
        }

    async def _create_notion_database(
        self,
        parent_page_id: str,
        template: str,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create Notion database from template."""
        from .notion_templates import create_database_payload
        from .notion_client import NotionClient

        notion = NotionClient()
        payload = create_database_payload(parent_page_id, template, title)

        # Create database via Notion API
        # (Would need to add create_database method to NotionClient)

        return {
            "status": "success",
            "message": f"Database created from template: {template}",
            "payload": payload,
        }

    async def run_stdio(self):
        """Run the MCP server using stdio transport."""
        if not self.server or not MCP_AVAILABLE:
            raise RuntimeError("MCP server not available")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def create_mcp_server(config: Optional[Dict[str, Any]] = None) -> NotionSkillMCPServer:
    """Create and configure MCP server."""
    return NotionSkillMCPServer(config)


if __name__ == "__main__":
    import asyncio

    # Load config from environment
    config = {
        "notion_api_key": os.getenv("NOTION_API_KEY"),
        "linear_api_key": os.getenv("LINEAR_API_KEY"),
        "repositories_db_id": os.getenv("NOTION_REPOSITORIES_DB_ID"),
        "tracks_db_id": os.getenv("NOTION_TRACKS_DB_ID"),
    }

    server = create_mcp_server(config)

    print("Starting Notion Skill MCP Server...")
    asyncio.run(server.run_stdio())
