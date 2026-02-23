"""
Conflict Resolution

Handles conflicts when the same entity is modified in multiple places:
- Git/conductor tracks vs Linear issues
- Notion manual edits vs automated sync
- Multiple source of truth scenarios
"""

import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class ConflictStrategy(Enum):
    """Strategy for resolving conflicts."""
    GIT_WINS = "git_wins"  # Always use Git/conductor as source of truth
    LINEAR_WINS = "linear_wins"  # Always use Linear as source of truth
    NOTION_WINS = "notion_wins"  # Preserve manual Notion edits
    NEWEST_WINS = "newest_wins"  # Use most recently updated
    OLDEST_WINS = "oldest_wins"  # Use oldest (most stable)
    MANUAL = "manual"  # Flag for human review
    MERGE = "merge"  # Attempt to merge changes


class ConflictType(Enum):
    """Type of conflict detected."""
    STATUS_MISMATCH = "status_mismatch"  # Track status differs
    TITLE_MISMATCH = "title_mismatch"  # Title/name differs
    PRIORITY_MISMATCH = "priority_mismatch"  # Priority differs
    ASSIGNEE_MISMATCH = "assignee_mismatch"  # Assignee differs
    CONTENT_MISMATCH = "content_mismatch"  # Description/content differs
    DELETED_IN_SOURCE = "deleted_in_source"  # Deleted in one source
    MODIFIED_CONCURRENTLY = "modified_concurrently"  # Modified in both at same time


@dataclass
class Conflict:
    """Represents a single conflict."""
    conflict_type: ConflictType
    entity_type: str  # "track", "issue", "repository"
    entity_id: str
    source_a: Dict[str, Any]  # e.g., Git/conductor
    source_b: Dict[str, Any]  # e.g., Linear
    source_a_updated: Optional[str]
    source_b_updated: Optional[str]
    suggested_resolution: Optional[ConflictStrategy] = None
    notes: str = ""


@dataclass
class ConflictResolution:
    """Result of conflict resolution."""
    conflict: Conflict
    strategy_used: ConflictStrategy
    resolved_value: Dict[str, Any]
    success: bool
    message: str


class ConflictResolver:
    """Resolves conflicts between data sources."""

    def __init__(self, default_strategy: ConflictStrategy = ConflictStrategy.NEWEST_WINS):
        """
        Initialize conflict resolver.

        Args:
            default_strategy: Default strategy to use when no specific rule applies
        """
        self.default_strategy = default_strategy
        self.custom_rules: Dict[str, ConflictStrategy] = {}
        self.resolution_history: List[ConflictResolution] = []

    def set_strategy(self, entity_type: str, strategy: ConflictStrategy):
        """
        Set a custom strategy for a specific entity type.

        Args:
            entity_type: Type of entity (e.g., "track", "issue")
            strategy: Strategy to use
        """
        self.custom_rules[entity_type] = strategy
        logger.info(f"Set conflict strategy for {entity_type}: {strategy.value}")

    def detect_conflicts(
        self,
        tracks: List[Dict[str, Any]],
        linear_issues: List[Dict[str, Any]],
        notion_data: Optional[Dict[str, Any]] = None,
    ) -> List[Conflict]:
        """
        Detect conflicts between sources.

        Args:
            tracks: Tracks from Git/conductor
            linear_issues: Issues from Linear
            notion_data: Optional data from Notion

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Create lookup maps
        track_map = {t["name"]: t for t in tracks}
        issue_map = {i["title"]: i for i in linear_issues}

        # Detect track vs Linear conflicts
        for track_name, track in track_map.items():
            if track_name in issue_map:
                issue = issue_map[track_name]
                track_conflicts = self._compare_track_and_issue(track_name, track, issue)
                conflicts.extend(track_conflicts)

        # Detect Notion conflicts if provided
        if notion_data:
            notion_conflicts = self._detect_notion_conflicts(tracks, linear_issues, notion_data)
            conflicts.extend(notion_conflicts)

        logger.info(f"Detected {len(conflicts)} conflicts")
        return conflicts

    def _compare_track_and_issue(
        self,
        name: str,
        track: Dict[str, Any],
        issue: Dict[str, Any],
    ) -> List[Conflict]:
        """Compare a track with a Linear issue."""
        conflicts = []

        # Status conflict
        track_status = track.get("status", "unknown")
        issue_status = issue.get("state", {}).get("name", "unknown")
        if self._statuses_differ(track_status, issue_status):
            conflicts.append(Conflict(
                conflict_type=ConflictType.STATUS_MISMATCH,
                entity_type="track_issue",
                entity_id=name,
                source_a={"name": name, "status": track_status, "source": "git"},
                source_b={"name": name, "status": issue_status, "source": "linear"},
                source_a_updated=track.get("completed_date"),
                source_b_updated=issue.get("completedAt") or issue.get("updatedAt"),
                suggested_resolution=self._suggest_status_resolution(track, issue),
                notes=f"Track status '{track_status}' vs Linear status '{issue_status}'"
            ))

        # Priority conflict
        track_priority = track.get("metadata", {}).get("priority", "P2")
        issue_priority = self._linear_priority_to_string(issue.get("priority"))
        if track_priority != issue_priority:
            conflicts.append(Conflict(
                conflict_type=ConflictType.PRIORITY_MISMATCH,
                entity_type="track_issue",
                entity_id=name,
                source_a={"name": name, "priority": track_priority, "source": "git"},
                source_b={"name": name, "priority": issue_priority, "source": "linear"},
                source_a_updated=track.get("completed_date"),
                source_b_updated=issue.get("updatedAt"),
                notes=f"Track priority '{track_priority}' vs Linear priority '{issue_priority}'"
            ))

        return conflicts

    def _detect_notion_conflicts(
        self,
        tracks: List[Dict[str, Any]],
        linear_issues: List[Dict[str, Any]],
        notion_data: Dict[str, Any],
    ) -> List[Conflict]:
        """Detect conflicts with Notion data."""
        conflicts = []

        # Check for manual Notion edits that differ from both sources
        notion_tracks = notion_data.get("tracks", {})

        for track in tracks:
            track_name = track["name"]
            if track_name in notion_tracks:
                notion_track = notion_tracks[track_name]

                # Check if Notion was updated more recently
                notion_updated = notion_track.get("updated_at")
                track_updated = track.get("completed_date")

                if notion_updated and track_updated:
                    if notion_updated > track_updated:
                        # Notion was updated after the track
                        conflicts.append(Conflict(
                            conflict_type=ConflictType.MODIFIED_CONCURRENTLY,
                            entity_type="track_notion",
                            entity_id=track_name,
                            source_a=track,
                            source_b=notion_track,
                            source_a_updated=track_updated,
                            source_b_updated=notion_updated,
                            suggested_resolution=ConflictStrategy.MANUAL,
                            notes="Notion was manually edited after last sync"
                        ))

        return conflicts

    def resolve_conflict(self, conflict: Conflict) -> ConflictResolution:
        """
        Resolve a single conflict.

        Args:
            conflict: The conflict to resolve

        Returns:
            Resolution result
        """
        # Get strategy for this entity type
        strategy = self.custom_rules.get(
            conflict.entity_type,
            self.default_strategy
        )

        # Use suggested resolution if available and not MANUAL
        if conflict.suggested_resolution and conflict.suggested_resolution != ConflictStrategy.MANUAL:
            strategy = conflict.suggested_resolution

        try:
            if strategy == ConflictStrategy.GIT_WINS:
                resolved = self._resolve_git_wins(conflict)
            elif strategy == ConflictStrategy.LINEAR_WINS:
                resolved = self._resolve_linear_wins(conflict)
            elif strategy == ConflictStrategy.NOTION_WINS:
                resolved = self._resolve_notion_wins(conflict)
            elif strategy == ConflictStrategy.NEWEST_WINS:
                resolved = self._resolve_newest_wins(conflict)
            elif strategy == ConflictStrategy.OLDEST_WINS:
                resolved = self._resolve_oldest_wins(conflict)
            elif strategy == ConflictStrategy.MANUAL:
                resolved = self._flag_for_manual_review(conflict)
            elif strategy == ConflictStrategy.MERGE:
                resolved = self._resolve_merge(conflict)
            else:
                resolved = ConflictResolution(
                    conflict=conflict,
                    strategy_used=strategy,
                    resolved_value={},
                    success=False,
                    message=f"Unknown strategy: {strategy}"
                )

            self.resolution_history.append(resolved)
            logger.info(f"Resolved conflict for {conflict.entity_id}: {strategy.value}")
            return resolved

        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return ConflictResolution(
                conflict=conflict,
                strategy_used=strategy,
                resolved_value={},
                success=False,
                message=f"Resolution failed: {str(e)}"
            )

    def _resolve_git_wins(self, conflict: Conflict) -> ConflictResolution:
        """Use Git/conductor as source of truth."""
        return ConflictResolution(
            conflict=conflict,
            strategy_used=ConflictStrategy.GIT_WINS,
            resolved_value=conflict.source_a,
            success=True,
            message="Using Git/conductor value"
        )

    def _resolve_linear_wins(self, conflict: Conflict) -> ConflictResolution:
        """Use Linear as source of truth."""
        return ConflictResolution(
            conflict=conflict,
            strategy_used=ConflictStrategy.LINEAR_WINS,
            resolved_value=conflict.source_b,
            success=True,
            message="Using Linear value"
        )

    def _resolve_notion_wins(self, conflict: Conflict) -> ConflictResolution:
        """Preserve manual Notion edits."""
        # For Notion wins, we keep the Notion value (source_b if Notion is second source)
        return ConflictResolution(
            conflict=conflict,
            strategy_used=ConflictStrategy.NOTION_WINS,
            resolved_value=conflict.source_b,
            success=True,
            message="Preserving manual Notion edit"
        )

    def _resolve_newest_wins(self, conflict: Conflict) -> ConflictResolution:
        """Use most recently updated value."""
        a_updated = conflict.source_a_updated or ""
        b_updated = conflict.source_b_updated or ""

        if a_updated >= b_updated:
            return ConflictResolution(
                conflict=conflict,
                strategy_used=ConflictStrategy.NEWEST_WINS,
                resolved_value=conflict.source_a,
                success=True,
                message=f"Source A is newer ({a_updated})"
            )
        else:
            return ConflictResolution(
                conflict=conflict,
                strategy_used=ConflictStrategy.NEWEST_WINS,
                resolved_value=conflict.source_b,
                success=True,
                message=f"Source B is newer ({b_updated})"
            )

    def _resolve_oldest_wins(self, conflict: Conflict) -> ConflictResolution:
        """Use oldest (most stable) value."""
        a_updated = conflict.source_a_updated or ""
        b_updated = conflict.source_b_updated or ""

        if a_updated <= b_updated:
            return ConflictResolution(
                conflict=conflict,
                strategy_used=ConflictStrategy.OLDEST_WINS,
                resolved_value=conflict.source_a,
                success=True,
                message=f"Source A is older ({a_updated})"
            )
        else:
            return ConflictResolution(
                conflict=conflict,
                strategy_used=ConflictStrategy.OLDEST_WINS,
                resolved_value=conflict.source_b,
                success=True,
                message=f"Source B is older ({b_updated})"
            )

    def _resolve_merge(self, conflict: Conflict) -> ConflictResolution:
        """Attempt to merge changes from both sources."""
        merged = {}

        # Merge non-conflicting fields
        for key in set(list(conflict.source_a.keys()) + list(conflict.source_b.keys())):
            if key in conflict.source_a and key in conflict.source_b:
                if conflict.source_a[key] == conflict.source_b[key]:
                    merged[key] = conflict.source_a[key]
                else:
                    # Conflict - use newer
                    if (conflict.source_a_updated or "") >= (conflict.source_b_updated or ""):
                        merged[key] = conflict.source_a.get(key)
                    else:
                        merged[key] = conflict.source_b.get(key)
            elif key in conflict.source_a:
                merged[key] = conflict.source_a[key]
            else:
                merged[key] = conflict.source_b[key]

        return ConflictResolution(
            conflict=conflict,
            strategy_used=ConflictStrategy.MERGE,
            resolved_value=merged,
            success=True,
            message="Merged values from both sources"
        )

    def _flag_for_manual_review(self, conflict: Conflict) -> ConflictResolution:
        """Flag conflict for human review."""
        return ConflictResolution(
            conflict=conflict,
            strategy_used=ConflictStrategy.MANUAL,
            resolved_value={},
            success=False,
            message="Requires manual review"
        )

    def _suggest_status_resolution(
        self,
        track: Dict[str, Any],
        issue: Dict[str, Any],
    ) -> Optional[ConflictStrategy]:
        """Suggest the best resolution for a status conflict."""
        track_status = track.get("status", "")
        issue_status = issue.get("state", {}).get("name", "")

        # If Linear is Done and track is complete, no conflict
        if issue_status.lower() in ["done", "complete", "closed"]:
            if track_status == "complete":
                return None  # No real conflict

        # If track is complete but Linear isn't, trust track
        if track_status == "complete" and issue_status.lower() not in ["done", "complete"]:
            return ConflictStrategy.GIT_WINS

        # If Linear is done but track isn't, trust Linear
        if issue_status.lower() == "done" and track_status != "complete":
            return ConflictStrategy.LINEAR_WINS

        return ConflictStrategy.NEWEST_WINS

    def _statuses_differ(self, status_a: str, status_b: str) -> bool:
        """Check if two statuses are meaningfully different."""
        # Normalize statuses
        complete_statuses = {"complete", "done", "closed", "completed"}
        active_statuses = {"active", "in_progress", "in progress", "open", "started"}

        a_complete = status_a.lower() in complete_statuses
        b_complete = status_b.lower() in complete_statuses

        # Both complete or both active = not a real conflict
        if a_complete == b_complete:
            return False

        return True

    def _linear_priority_to_string(self, priority: Optional[int]) -> str:
        """Convert Linear priority number to string."""
        priority_map = {
            0: "No priority",
            1: "Urgent",
            2: "High",
            3: "Medium",
            4: "Low",
            None: "No priority",
        }
        # Map to P0-P4 format
        if priority is None:
            return "P2"
        return f"P{priority}" if priority <= 4 else "P2"

    def get_resolution_report(self) -> Dict[str, Any]:
        """Generate a report of all resolutions."""
        successful = [r for r in self.resolution_history if r.success]
        failed = [r for r in self.resolution_history if not r.success]
        manual = [r for r in self.resolution_history if r.strategy_used == ConflictStrategy.MANUAL]

        return {
            "total_conflicts": len(self.resolution_history),
            "resolved": len(successful),
            "failed": len(failed),
            "manual_review_required": len(manual),
            "success_rate": len(successful) / len(self.resolution_history) if self.resolution_history else 1.0,
            "failed_resolutions": [
                {
                    "entity": r.conflict.entity_id,
                    "type": r.conflict.conflict_type.value,
                    "message": r.message,
                }
                for r in failed
            ],
            "manual_review_items": [
                {
                    "entity": r.conflict.entity_id,
                    "type": r.conflict.conflict_type.value,
                    "notes": r.conflict.notes,
                }
                for r in manual
            ],
        }
