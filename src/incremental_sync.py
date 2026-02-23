"""
Incremental Sync & Change Detection

Detects changes since last sync and only syncs what changed.
Reduces API calls, improves speed, and avoids rate limits.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SyncState:
    """Represents the state of a repository at sync time."""
    timestamp: str
    repo_path: str
    last_commit_sha: str
    tracks: List[Dict[str, Any]]
    track_hashes: Dict[str, str]  # track_name -> hash of track data
    linear_project_id: Optional[str]
    linear_issue_hashes: Dict[str, str]  # issue_id -> hash
    notion_page_ids: Dict[str, str]  # entity_type:id -> notion_page_id
    sync_stats: Dict[str, Any]


@dataclass
class ChangeSet:
    """Represents changes detected since last sync."""
    has_changes: bool
    new_tracks: List[Dict[str, Any]]
    updated_tracks: List[Dict[str, Any]]
    deleted_tracks: List[Dict[str, Any]]
    new_commits: List[Dict[str, Any]]
    linear_issues_changed: bool
    linear_new_issues: List[Dict[str, Any]]
    linear_updated_issues: List[Dict[str, Any]]
    metadata_changed: bool
    summary: str


class IncrementalSyncManager:
    """Manages incremental synchronization with change detection."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize incremental sync manager.

        Args:
            cache_dir: Directory to store sync state cache. Defaults to repo/.notion-cache
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def _get_cache_path(self, repo_path: str) -> Path:
        """Get cache file path for a repository."""
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            repo_hash = hashlib.md5(str(repo_path).encode()).hexdigest()[:8]
            return self.cache_dir / f"sync_state_{repo_hash}.json"
        else:
            return Path(repo_path) / ".notion-sync-cache.json"

    def load_last_sync_state(self, repo_path: str) -> Optional[SyncState]:
        """
        Load the last sync state for a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            SyncState if found, None otherwise
        """
        cache_file = self._get_cache_path(repo_path)

        if not cache_file.exists():
            logger.info(f"No previous sync state found for {repo_path}")
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"Loaded sync state from {cache_file}")
            return SyncState(**data)

        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")
            return None

    def save_sync_state(self, repo_path: str, state: SyncState):
        """
        Save sync state for a repository.

        Args:
            repo_path: Path to the repository
            state: SyncState to save
        """
        cache_file = self._get_cache_path(repo_path)

        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(asdict(state), f, indent=2)

            logger.info(f"Saved sync state to {cache_file}")

        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def _compute_track_hash(self, track: Dict[str, Any]) -> str:
        """Compute a hash for a track to detect changes."""
        # Hash the important fields that indicate a change
        content = json.dumps({
            "name": track.get("name"),
            "status": track.get("status"),
            "commit_sha": track.get("commit_sha"),
            "completed_date": track.get("completed_date"),
            "priority": track.get("metadata", {}).get("priority"),
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _compute_issue_hash(self, issue: Dict[str, Any]) -> str:
        """Compute a hash for a Linear issue to detect changes."""
        content = json.dumps({
            "id": issue.get("id"),
            "title": issue.get("title"),
            "state": issue.get("state", {}).get("name"),
            "priority": issue.get("priority"),
            "assignee": issue.get("assignee", {}).get("id") if issue.get("assignee") else None,
            "completedAt": issue.get("completedAt"),
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def detect_changes(
        self,
        repo_path: str,
        current_tracks: List[Dict[str, Any]],
        current_commits: List[Dict[str, Any]],
        current_linear_issues: Optional[List[Dict[str, Any]]] = None,
        linear_project_id: Optional[str] = None,
    ) -> ChangeSet:
        """
        Detect changes since last sync.

        Args:
            repo_path: Path to the repository
            current_tracks: Current list of tracks from repository
            current_commits: Current list of recent commits
            current_linear_issues: Current Linear issues (optional)
            linear_project_id: Linear project ID (optional)

        Returns:
            ChangeSet describing what changed
        """
        # Load last sync state
        last_state = self.load_last_sync_state(repo_path)

        if last_state is None:
            # First sync - everything is new
            logger.info("First sync detected - all items are new")
            return ChangeSet(
                has_changes=True,
                new_tracks=current_tracks,
                updated_tracks=[],
                deleted_tracks=[],
                new_commits=current_commits,
                linear_issues_changed=current_linear_issues is not None,
                linear_new_issues=current_linear_issues or [],
                linear_updated_issues=[],
                metadata_changed=True,
                summary=f"Initial sync: {len(current_tracks)} tracks, {len(current_commits)} commits"
            )

        # Compute hashes for current tracks
        current_track_hashes = {
            track["name"]: self._compute_track_hash(track)
            for track in current_tracks
        }

        # Detect track changes
        new_tracks = []
        updated_tracks = []
        deleted_tracks = []

        # Check for new and updated tracks
        for track in current_tracks:
            track_name = track["name"]
            current_hash = current_track_hashes[track_name]

            if track_name not in last_state.track_hashes:
                # New track
                new_tracks.append(track)
                logger.debug(f"New track detected: {track_name}")
            elif last_state.track_hashes[track_name] != current_hash:
                # Updated track
                updated_tracks.append(track)
                logger.debug(f"Updated track detected: {track_name}")

        # Check for deleted tracks
        last_track_names = set(last_state.track_hashes.keys())
        current_track_names = set(current_track_hashes.keys())
        deleted_track_names = last_track_names - current_track_names

        for track_name in deleted_track_names:
            # Find the track in last state (we only have the name)
            deleted_tracks.append({
                "name": track_name,
                "status": "deleted",
                "last_synced": last_state.timestamp,
            })
            logger.debug(f"Deleted track detected: {track_name}")

        # Detect new commits
        last_commit_sha = last_state.last_commit_sha
        new_commits = []

        for commit in current_commits:
            if commit["sha"] == last_commit_sha:
                break  # Reached the last synced commit
            new_commits.append(commit)

        # Detect Linear issue changes
        linear_new_issues = []
        linear_updated_issues = []
        linear_issues_changed = False

        if current_linear_issues is not None:
            current_issue_hashes = {
                issue["id"]: self._compute_issue_hash(issue)
                for issue in current_linear_issues
            }

            for issue in current_linear_issues:
                issue_id = issue["id"]
                current_hash = current_issue_hashes[issue_id]

                if issue_id not in last_state.linear_issue_hashes:
                    linear_new_issues.append(issue)
                    linear_issues_changed = True
                elif last_state.linear_issue_hashes[issue_id] != current_hash:
                    linear_updated_issues.append(issue)
                    linear_issues_changed = True

        # Check metadata changes
        metadata_changed = (
            last_state.linear_project_id != linear_project_id
        )

        # Build summary
        summary_parts = []
        if new_tracks:
            summary_parts.append(f"{len(new_tracks)} new tracks")
        if updated_tracks:
            summary_parts.append(f"{len(updated_tracks)} updated tracks")
        if deleted_tracks:
            summary_parts.append(f"{len(deleted_tracks)} deleted tracks")
        if new_commits:
            summary_parts.append(f"{len(new_commits)} new commits")
        if linear_new_issues:
            summary_parts.append(f"{len(linear_new_issues)} new Linear issues")
        if linear_updated_issues:
            summary_parts.append(f"{len(linear_updated_issues)} updated Linear issues")

        has_changes = bool(
            new_tracks or updated_tracks or deleted_tracks or
            new_commits or linear_issues_changed or metadata_changed
        )

        return ChangeSet(
            has_changes=has_changes,
            new_tracks=new_tracks,
            updated_tracks=updated_tracks,
            deleted_tracks=deleted_tracks,
            new_commits=new_commits,
            linear_issues_changed=linear_issues_changed,
            linear_new_issues=linear_new_issues,
            linear_updated_issues=linear_updated_issues,
            metadata_changed=metadata_changed,
            summary="; ".join(summary_parts) if summary_parts else "No changes detected"
        )

    def create_sync_state(
        self,
        repo_path: str,
        tracks: List[Dict[str, Any]],
        commits: List[Dict[str, Any]],
        linear_issues: Optional[List[Dict[str, Any]]] = None,
        linear_project_id: Optional[str] = None,
        notion_page_ids: Optional[Dict[str, str]] = None,
        sync_stats: Optional[Dict[str, Any]] = None,
    ) -> SyncState:
        """
        Create a new SyncState from current data.

        Args:
            repo_path: Path to the repository
            tracks: Current tracks
            commits: Current commits (most recent first)
            linear_issues: Current Linear issues
            linear_project_id: Linear project ID
            notion_page_ids: Notion page ID mappings
            sync_stats: Sync statistics

        Returns:
            New SyncState object
        """
        return SyncState(
            timestamp=datetime.now().isoformat(),
            repo_path=str(repo_path),
            last_commit_sha=commits[0]["sha"] if commits else None,
            tracks=tracks,
            track_hashes={
                track["name"]: self._compute_track_hash(track)
                for track in tracks
            },
            linear_project_id=linear_project_id,
            linear_issue_hashes={
                issue["id"]: self._compute_issue_hash(issue)
                for issue in (linear_issues or [])
            },
            notion_page_ids=notion_page_ids or {},
            sync_stats=sync_stats or {}
        )

    def should_skip_sync(self, changes: ChangeSet, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if sync should be skipped based on changes and config.

        Args:
            changes: Detected changes
            config: Sync configuration

        Returns:
            Tuple of (should_skip, reason)
        """
        if not changes.has_changes:
            return True, "No changes detected"

        # Check if only deleted tracks (may want to skip)
        if config.get("skip_delete_only", False):
            if not changes.new_tracks and not changes.updated_tracks and changes.deleted_tracks:
                return True, "Only deleted tracks and skip_delete_only is enabled"

        # Check minimum change threshold
        min_changes = config.get("min_changes_threshold", 0)
        total_changes = (
            len(changes.new_tracks) +
            len(changes.updated_tracks) +
            len(changes.new_commits)
        )
        if total_changes < min_changes:
            return True, f"Only {total_changes} changes (threshold: {min_changes})"

        return False, ""

    def get_sync_preview(self, changes: ChangeSet) -> str:
        """
        Generate a human-readable preview of pending changes.

        Args:
            changes: Detected changes

        Returns:
            Formatted preview string
        """
        lines = ["\n📋 Sync Preview", "=" * 50]

        if changes.new_tracks:
            lines.append(f"\n✅ New Tracks ({len(changes.new_tracks)}):")
            for track in changes.new_tracks[:10]:  # Limit display
                lines.append(f"  • {track['name']} ({track.get('status', 'unknown')})")
            if len(changes.new_tracks) > 10:
                lines.append(f"  ... and {len(changes.new_tracks) - 10} more")

        if changes.updated_tracks:
            lines.append(f"\n🔄 Updated Tracks ({len(changes.updated_tracks)}):")
            for track in changes.updated_tracks[:10]:
                lines.append(f"  • {track['name']} → {track.get('status', 'unknown')}")
            if len(changes.updated_tracks) > 10:
                lines.append(f"  ... and {len(changes.updated_tracks) - 10} more")

        if changes.deleted_tracks:
            lines.append(f"\n❌ Deleted Tracks ({len(changes.deleted_tracks)}):")
            for track in changes.deleted_tracks[:10]:
                lines.append(f"  • {track['name']}")
            if len(changes.deleted_tracks) > 10:
                lines.append(f"  ... and {len(changes.deleted_tracks) - 10} more")

        if changes.new_commits:
            lines.append(f"\n💾 New Commits ({len(changes.new_commits)}):")
            for commit in changes.new_commits[:5]:
                msg = commit["message"][:50] + "..." if len(commit["message"]) > 50 else commit["message"]
                lines.append(f"  • {commit['sha'][:7]} {msg}")
            if len(changes.new_commits) > 5:
                lines.append(f"  ... and {len(changes.new_commits) - 5} more")

        if changes.linear_new_issues:
            lines.append(f"\n🔵 New Linear Issues ({len(changes.linear_new_issues)}):")
            for issue in changes.linear_new_issues[:10]:
                lines.append(f"  • {issue.get('title', 'Untitled')}")

        if changes.linear_updated_issues:
            lines.append(f"\n🟡 Updated Linear Issues ({len(changes.linear_updated_issues)}):")
            for issue in changes.linear_updated_issues[:10]:
                lines.append(f"  • {issue.get('title', 'Untitled')} → {issue.get('state', {}).get('name', 'unknown')}")

        lines.append("\n" + "=" * 50)
        lines.append(f"Summary: {changes.summary}")

        return "\n".join(lines)
