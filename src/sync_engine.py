"""
Sync Engine

Orchestrates the synchronization between:
- Git repositories
- Linear projects
- Notion databases

Supports incremental sync with change detection.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .notion_client import NotionClient
from .linear_client import LinearClient
from .git_analyzer import GitAnalyzer
from .track_parser import TrackParser
from .incremental_sync import IncrementalSyncManager, SyncState, ChangeSet

logger = logging.getLogger(__name__)


class SyncEngine:
    """Main synchronization engine."""

    def __init__(
        self,
        notion_client: Optional[NotionClient] = None,
        linear_client: Optional[LinearClient] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize sync engine.

        Args:
            notion_client: Notion API client
            linear_client: Linear API client
            config: Sync configuration
        """
        self.notion = notion_client or NotionClient()
        self.linear = linear_client or LinearClient()
        self.config = config or {}
        self.incremental_manager = IncrementalSyncManager(
            config.get("cache_dir") if config else None
        )

        # Database IDs from config or environment
        self.repositories_db_id = (
            config.get("repositories_db_id")
            or os.getenv("NOTION_REPOSITORIES_DB_ID")
        )
        self.tracks_db_id = (
            config.get("tracks_db_id")
            or os.getenv("NOTION_TRACKS_DB_ID")
        )
        self.linear_projects_db_id = (
            config.get("linear_projects_db_id")
            or os.getenv("NOTION_LINEAR_PROJECTS_DB_ID")
        )

    def sync_repository(
        self,
        repo_path: str,
        force: bool = False,
        preview: bool = False,
    ) -> Dict[str, Any]:
        """
        Sync a complete repository to Notion.

        Args:
            repo_path: Path to the repository
            force: Force full sync even if no changes detected
            preview: Only detect changes, don't sync

        Returns:
            Sync result with statistics
        """
        repo_path = Path(repo_path).resolve()
        logger.info(f"Starting sync for repository: {repo_path}")

        result = {
            "success": True,
            "repository": str(repo_path),
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "errors": [],
            "changes_detected": None,
            "sync_skipped": False,
            "sync_mode": "incremental",
        }

        try:
            # Step 1: Analyze repository
            logger.info("Step 1: Analyzing repository...")
            git_analyzer = GitAnalyzer(str(repo_path))
            repo_metadata = git_analyzer.get_repository_metadata()
            recent_commits = git_analyzer.get_recent_commits(50)  # Get more for change detection
            result["steps"].append({
                "name": "Repository Analysis",
                "status": "complete",
                "data": repo_metadata,
            })

            # Step 2: Parse conductor tracks
            logger.info("Step 2: Parsing conductor tracks...")
            track_parser = TrackParser(str(repo_path))
            tracks = track_parser.parse_tracks_file()
            archived_tracks = track_parser.parse_all_archived_tracks()
            track_summary = track_parser.get_track_summary()
            all_tracks = tracks + archived_tracks
            result["steps"].append({
                "name": "Track Parsing",
                "status": "complete",
                "data": {
                    "active_tracks": len(tracks),
                    "archived_tracks": len(archived_tracks),
                    "summary": track_summary,
                },
            })

            # Step 3: Find matching Linear project
            logger.info("Step 3: Finding Linear project...")
            linear_project = self._find_linear_project(repo_metadata["name"], repo_path)
            linear_issues = []
            linear_project_id = None
            if linear_project:
                linear_project_id = linear_project["id"]
                linear_issues = self.linear.get_issues(project_id=linear_project["id"])
            result["steps"].append({
                "name": "Linear Integration",
                "status": "complete",
                "data": {
                    "linear_project": linear_project.get("name") if linear_project else None,
                    "issue_count": len(linear_issues),
                },
            })

            # Step 4: Detect changes (incremental sync)
            logger.info("Step 4: Detecting changes...")
            changes = self.incremental_manager.detect_changes(
                repo_path=str(repo_path),
                current_tracks=all_tracks,
                current_commits=recent_commits,
                current_linear_issues=linear_issues,
                linear_project_id=linear_project_id,
            )
            result["changes_detected"] = {
                "has_changes": changes.has_changes,
                "summary": changes.summary,
                "new_tracks": len(changes.new_tracks),
                "updated_tracks": len(changes.updated_tracks),
                "deleted_tracks": len(changes.deleted_tracks),
                "new_commits": len(changes.new_commits),
                "linear_issues_changed": changes.linear_issues_changed,
            }

            # Check if we should skip sync
            if not force:
                should_skip, skip_reason = self.incremental_manager.should_skip_sync(
                    changes, self.config
                )
                if should_skip:
                    logger.info(f"Skipping sync: {skip_reason}")
                    result["sync_skipped"] = True
                    result["skip_reason"] = skip_reason
                    result["steps"].append({
                        "name": "Change Detection",
                        "status": "complete",
                        "data": {"skipped": True, "reason": skip_reason},
                    })
                    return result

            # Show preview if requested
            if preview:
                result["preview"] = self.incremental_manager.get_sync_preview(changes)
                result["steps"].append({
                    "name": "Preview Mode",
                    "status": "complete",
                    "data": {"preview_only": True},
                })
                return result

            result["sync_mode"] = "full" if not changes.has_changes else "incremental"

            # Step 5: Create/update Notion pages
            logger.info(f"Step 5: Syncing to Notion ({result['sync_mode']})...")
            notion_page = self._sync_to_notion_incremental(
                repo_metadata=repo_metadata,
                changes=changes,
                linear_project=linear_project,
                linear_issues=linear_issues,
            )
            result["steps"].append({
                "name": "Notion Sync",
                "status": "complete",
                "data": {
                    "page_id": notion_page.get("id") if notion_page else None,
                    "page_url": notion_page.get("url") if notion_page else None,
                    "mode": result["sync_mode"],
                },
            })

            # Save sync state
            sync_state = self.incremental_manager.create_sync_state(
                repo_path=str(repo_path),
                tracks=all_tracks,
                commits=recent_commits,
                linear_issues=linear_issues,
                linear_project_id=linear_project_id,
                notion_page_ids={"repository": notion_page["id"]} if notion_page else {},
                sync_stats=result,
            )
            self.incremental_manager.save_sync_state(str(repo_path), sync_state)

            result["summary"] = {
                "repository_name": repo_metadata.get("name"),
                "total_tracks": track_summary.get("total_tracks", 0),
                "completed_tracks": track_summary.get("completed_tracks", 0),
                "linear_project": linear_project.get("name") if linear_project else "Not linked",
                "notion_page": notion_page.get("url") if notion_page else "Not created",
                "sync_mode": result["sync_mode"],
                "changes_synced": changes.summary,
            }

            logger.info(f"Sync completed successfully for {repo_path}")

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            result["success"] = False
            result["errors"].append(str(e))

        return result

    def _find_linear_project(
        self,
        repo_name: str,
        repo_path: Path,
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching Linear project for a repository.

        Args:
            repo_name: Repository name
            repo_path: Path to repository

        Returns:
            Linear project or None
        """
        # Try explicit mapping first
        config_file = repo_path / ".notion-sync.json"
        if config_file.exists():
            import json
            with open(config_file, "r") as f:
                config = json.load(f)
                if config.get("linearProjectId"):
                    return self.linear.get_project(config["linearProjectId"])

        # Try name matching
        projects = self.linear.search_projects(repo_name)
        if projects:
            return projects[0]

        # Try without hyphens/underscores
        normalized_name = repo_name.replace("-", " ").replace("_", " ")
        projects = self.linear.search_projects(normalized_name)
        if projects:
            return projects[0]

        logger.warning(f"No matching Linear project found for {repo_name}")
        return None

    def _sync_to_notion_incremental(
        self,
        repo_metadata: Dict[str, Any],
        changes: "ChangeSet",
        linear_project: Optional[Dict[str, Any]],
        linear_issues: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Sync data to Notion incrementally (only changed items).

        Args:
            repo_metadata: Repository metadata
            changes: Detected changes from incremental sync
            linear_project: Linear project (if linked)
            linear_issues: List of Linear issues

        Returns:
            Created/updated Notion page
        """
        if not self.repositories_db_id:
            logger.warning("Notion repositories database ID not configured")
            return None

        # Check if page already exists
        existing_page = self.notion.find_page_by_title(
            self.repositories_db_id,
            repo_metadata.get("name", ""),
        )

        # Prepare properties (same as full sync)
        properties = {
            "Name": {
                "title": [{"text": {"content": repo_metadata.get("name", "")}}]
            },
            "Description": {
                "rich_text": [{"text": {"content": repo_metadata.get("description", "")}}]
            },
            "Path": {
                "rich_text": [{"text": {"content": repo_metadata.get("path", "")}}]
            },
            "Primary Language": {
                "select": {"name": repo_metadata.get("primary_language", "Unknown")}
            },
            "Last Commit": {
                "date": {"start": repo_metadata.get("last_commit_date")[:10]}
                if repo_metadata.get("last_commit_date")
                else None
            },
            "Last Commit Author": {
                "rich_text": [{"text": {"content": repo_metadata.get("last_commit_author", "")}}]
            },
            "Last Commit Message": {
                "rich_text": [{"text": {"content": repo_metadata.get("last_commit_message", "")}}]
            },
            "Has Conductor": {
                "checkbox": repo_metadata.get("has_conductor", False)
            },
            "Track Count": {
                "number": len(changes.new_tracks) + len(changes.updated_tracks)
            },
            "Status": {
                "select": {"name": "Active"}
            },
        }

        # Add Linear project relation if linked
        if linear_project and self.linear_projects_db_id:
            linear_page = self.notion.find_page_by_title(
                self.linear_projects_db_id,
                linear_project.get("name", ""),
            )
            if linear_page:
                properties["Linear Project"] = {
                    "relation": [{"id": linear_page["id"]}]
                }

        # Create or update page
        if existing_page:
            page = self.notion.update_page(
                page_id=existing_page["id"],
                properties=properties,
            )
            logger.info(f"Updated existing Notion page: {page['id']}")
        else:
            page = self.notion.create_page(
                parent_database_id=self.repositories_db_id,
                properties=properties,
            )
            logger.info(f"Created new Notion page: {page['id']}")

        # Sync only changed tracks
        if self.tracks_db_id:
            # Sync new tracks
            if changes.new_tracks:
                logger.info(f"Syncing {len(changes.new_tracks)} new tracks...")
                self._sync_tracks_to_notion(changes.new_tracks, page["id"], operation="create")

            # Sync updated tracks
            if changes.updated_tracks:
                logger.info(f"Syncing {len(changes.updated_tracks)} updated tracks...")
                self._sync_tracks_to_notion(changes.updated_tracks, page["id"], operation="update")

            # Handle deleted tracks
            if changes.deleted_tracks:
                logger.info(f"Handling {len(changes.deleted_tracks)} deleted tracks...")
                self._handle_deleted_tracks(changes.deleted_tracks, page["id"])

        # Sync Linear issues if available
        if linear_issues and self.linear_projects_db_id:
            if changes.linear_issues_changed:
                logger.info("Syncing changed Linear issues...")
                self._sync_linear_issues_to_notion(
                    changes.linear_new_issues + changes.linear_updated_issues,
                    linear_project,
                    page["id"],
                )

        return page

    def _sync_to_notion(
        self,
        repo_metadata: Dict[str, Any],
        tracks: List[Dict[str, Any]],
        linear_project: Optional[Dict[str, Any]],
        linear_issues: List[Dict[str, Any]],
        recent_commits: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Sync data to Notion (full sync - legacy method).

        Args:
            repo_metadata: Repository metadata
            tracks: List of tracks
            linear_project: Linear project (if linked)
            linear_issues: List of Linear issues
            recent_commits: Recent commits

        Returns:
            Created/updated Notion page
        """
        if not self.repositories_db_id:
            logger.warning("Notion repositories database ID not configured")
            return None

        # Check if page already exists
        existing_page = self.notion.find_page_by_title(
            self.repositories_db_id,
            repo_metadata.get("name", ""),
        )

        # Prepare properties
        properties = {
            "Name": {
                "title": [{"text": {"content": repo_metadata.get("name", "")}}]
            },
            "Description": {
                "rich_text": [{"text": {"content": repo_metadata.get("description", "")}}]
            },
            "Path": {
                "rich_text": [{"text": {"content": repo_metadata.get("path", "")}}]
            },
            "Primary Language": {
                "select": {"name": repo_metadata.get("primary_language", "Unknown")}
            },
            "Last Commit": {
                "date": {"start": repo_metadata.get("last_commit_date")[:10]}
                if repo_metadata.get("last_commit_date")
                else None
            },
            "Last Commit Author": {
                "rich_text": [{"text": {"content": repo_metadata.get("last_commit_author", "")}}]
            },
            "Last Commit Message": {
                "rich_text": [{"text": {"content": repo_metadata.get("last_commit_message", "")}}]
            },
            "Has Conductor": {
                "checkbox": repo_metadata.get("has_conductor", False)
            },
            "Track Count": {
                "number": len(tracks)
            },
            "Status": {
                "select": {"name": "Active"}
            },
        }

        # Add Linear project relation if linked
        if linear_project and self.linear_projects_db_id:
            linear_page = self.notion.find_page_by_title(
                self.linear_projects_db_id,
                linear_project.get("name", ""),
            )
            if linear_page:
                properties["Linear Project"] = {
                    "relation": [{"id": linear_page["id"]}]
                }

        # Create or update page
        if existing_page:
            page = self.notion.update_page(
                page_id=existing_page["id"],
                properties=properties,
            )
            logger.info(f"Updated existing Notion page: {page['id']}")
        else:
            page = self.notion.create_page(
                parent_database_id=self.repositories_db_id,
                properties=properties,
            )
            logger.info(f"Created new Notion page: {page['id']}")

        # Sync tracks to Notion
        if self.tracks_db_id:
            self._sync_tracks_to_notion(tracks, page["id"])

        # Sync Linear issues if available
        if linear_issues and self.linear_projects_db_id:
            self._sync_linear_issues_to_notion(linear_issues, linear_project, page["id"])

        return page

    def _sync_tracks_to_notion(
        self,
        tracks: List[Dict[str, Any]],
        repository_page_id: str,
    ):
        """Sync tracks to Notion database."""
        if not self.tracks_db_id:
            return

        for track in tracks:
            # Check if track already exists
            existing = self.notion.find_page_by_title(
                self.tracks_db_id,
                track.get("name", ""),
            )

            # Map status
            status_map = {
                "complete": "Complete",
                "in_progress": "In Progress",
                "active": "Active",
                "archived": "Archived",
                "planning": "Planning",
            }
            notion_status = status_map.get(track.get("status", ""), "Planning")

            properties = {
                "Track Name": {
                    "title": [{"text": {"content": track.get("name", "")}}]
                },
                "Repository": {
                    "relation": [{"id": repository_page_id}]
                },
                "Status": {
                    "select": {"name": notion_status}
                },
                "Priority": {
                    "select": {"name": track.get("metadata", {}).get("priority", "P2")}
                },
                "Commit SHA": {
                    "rich_text": [{"text": {"content": track.get("commit_sha", "")}}]
                },
            }

            if track.get("completed_date"):
                properties["Completed Date"] = {
                    "date": {"start": track["completed_date"][:10]}
                }

            if track.get("archive_path"):
                properties["Archive Path"] = {
                    "url": track["archive_path"]
                }

            if existing:
                self.notion.update_page(page_id=existing["id"], properties=properties)
            else:
                self.notion.create_page(
                    parent_database_id=self.tracks_db_id,
                    properties=properties,
                )

    def _sync_tracks_to_notion(
        self,
        tracks: List[Dict[str, Any]],
        repository_page_id: str,
        operation: str = "create",
    ):
        """
        Sync tracks to Notion database.

        Args:
            tracks: List of tracks to sync
            repository_page_id: ID of the repository page
            operation: "create", "update", or "sync"
        """
        if not self.tracks_db_id:
            return

        for track in tracks:
            # Check if track already exists
            existing = self.notion.find_page_by_title(
                self.tracks_db_id,
                track.get("name", ""),
            )

            # Map status
            status_map = {
                "complete": "Complete",
                "in_progress": "In Progress",
                "active": "Active",
                "archived": "Archived",
                "planning": "Planning",
            }
            notion_status = status_map.get(track.get("status", ""), "Planning")

            properties = {
                "Track Name": {
                    "title": [{"text": {"content": track.get("name", "")}}]
                },
                "Repository": {
                    "relation": [{"id": repository_page_id}]
                },
                "Status": {
                    "select": {"name": notion_status}
                },
                "Priority": {
                    "select": {"name": track.get("metadata", {}).get("priority", "P2")}
                },
                "Commit SHA": {
                    "rich_text": [{"text": {"content": track.get("commit_sha", "")}}]
                },
            }

            if track.get("completed_date"):
                properties["Completed Date"] = {
                    "date": {"start": track["completed_date"][:10]}
                }

            if track.get("archive_path"):
                properties["Archive Path"] = {
                    "url": track["archive_path"]
                }

            # Handle based on operation
            if operation == "create" and not existing:
                self.notion.create_page(
                    parent_database_id=self.tracks_db_id,
                    properties=properties,
                )
            elif operation == "update" and existing:
                self.notion.update_page(page_id=existing["id"], properties=properties)
            elif operation == "sync":
                # Sync always creates or updates
                if existing:
                    self.notion.update_page(page_id=existing["id"], properties=properties)
                else:
                    self.notion.create_page(
                        parent_database_id=self.tracks_db_id,
                        properties=properties,
                    )

    def _handle_deleted_tracks(
        self,
        deleted_tracks: List[Dict[str, Any]],
        repository_page_id: str,
    ):
        """
        Handle tracks that were deleted from the repository.

        Args:
            deleted_tracks: List of deleted track information
            repository_page_id: ID of the repository page
        """
        if not self.tracks_db_id:
            return

        for track in deleted_tracks:
            # Find the track in Notion
            existing = self.notion.find_page_by_title(
                self.tracks_db_id,
                track.get("name", ""),
            )

            if existing:
                # Option 1: Archive the track (don't delete)
                self.notion.update_page(
                    page_id=existing["id"],
                    properties={
                        "Status": {"select": {"name": "Archived"}},
                    },
                )
                logger.info(f"Archived deleted track: {track.get('name')}")

                # Option 2: Add deletion note (could be added as a comment)
                # self.notion.add_comment(...)

    def _sync_linear_issues_to_notion(
        self,
        issues: List[Dict[str, Any]],
        linear_project: Dict[str, Any],
        repository_page_id: str,
    ):
        """Sync Linear issues to Notion."""
        # This would create/update issue entries in Notion
        # For now, just log the count
        logger.info(f"Would sync {len(issues)} Linear issues to Notion")

    def sync_all_repositories(self, base_path: str) -> List[Dict[str, Any]]:
        """
        Sync all repositories in a directory.

        Args:
            base_path: Base directory to search for repositories

        Returns:
            List of sync results
        """
        base_path = Path(base_path)
        results = []

        # Find all directories with .git folders
        for item in base_path.iterdir():
            if not item.is_dir():
                continue

            git_dir = item / ".git"
            if not git_dir.exists():
                continue

            logger.info(f"Found repository: {item.name}")
            result = self.sync_repository(str(item))
            results.append(result)

        return results

    def get_sync_status(self, repo_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Get sync status for multiple repositories.

        Args:
            repo_paths: List of repository paths

        Returns:
            List of status information
        """
        statuses = []

        for repo_path in repo_paths:
            # Check if sync config exists
            config_file = Path(repo_path) / ".notion-sync.json"
            is_configured = config_file.exists()

            # Get last sync time (would be stored in config or database)
            last_sync = "Never"

            statuses.append({
                "repository": Path(repo_path).name,
                "configured": is_configured,
                "last_sync": last_sync,
                "status": "Synced" if last_sync != "Never" else "Not synced",
            })

        return statuses
