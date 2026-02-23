"""
Tests for Conflict Resolution Module
"""

import pytest
from src.conflict_resolution import (
    ConflictResolver,
    ConflictStrategy,
    ConflictType,
    Conflict,
)


class TestConflictResolver:
    """Tests for ConflictResolver."""

    def test_init_default_strategy(self):
        """Test initialization with default strategy."""
        resolver = ConflictResolver()
        assert resolver.default_strategy == ConflictStrategy.NEWEST_WINS

    def test_set_strategy(self):
        """Test setting custom strategy."""
        resolver = ConflictResolver()
        resolver.set_strategy("track", ConflictStrategy.GIT_WINS)
        
        assert resolver.custom_rules["track"] == ConflictStrategy.GIT_WINS

    def test_detect_status_conflict(self):
        """Test detection of status conflicts."""
        resolver = ConflictResolver()
        
        tracks = [
            {
                "name": "test_track",
                "status": "complete",
                "completed_date": "2026-02-23",
            }
        ]
        
        linear_issues = [
            {
                "title": "test_track",
                "state": {"name": "In Progress"},
                "priority": 2,
                "updatedAt": "2026-02-22",
            }
        ]
        
        conflicts = resolver.detect_conflicts(tracks, linear_issues)
        
        assert len(conflicts) > 0
        assert any(c.conflict_type == ConflictType.STATUS_MISMATCH for c in conflicts)

    def test_resolve_git_wins(self):
        """Test git_wins resolution strategy."""
        resolver = ConflictResolver(ConflictStrategy.GIT_WINS)
        
        conflict = Conflict(
            conflict_type=ConflictType.STATUS_MISMATCH,
            entity_type="track",
            entity_id="test_track",
            source_a={"status": "complete", "source": "git"},
            source_b={"status": "In Progress", "source": "linear"},
            source_a_updated="2026-02-23",
            source_b_updated="2026-02-22",
        )
        
        resolution = resolver.resolve_conflict(conflict)
        
        assert resolution.success is True
        assert resolution.strategy_used == ConflictStrategy.GIT_WINS
        assert resolution.resolved_value == conflict.source_a

    def test_resolve_linear_wins(self):
        """Test linear_wins resolution strategy."""
        resolver = ConflictResolver(ConflictStrategy.LINEAR_WINS)
        
        conflict = Conflict(
            conflict_type=ConflictType.STATUS_MISMATCH,
            entity_type="track",
            entity_id="test_track",
            source_a={"status": "complete", "source": "git"},
            source_b={"status": "In Progress", "source": "linear"},
            source_a_updated="2026-02-23",
            source_b_updated="2026-02-22",
        )
        
        resolution = resolver.resolve_conflict(conflict)
        
        assert resolution.success is True
        assert resolution.strategy_used == ConflictStrategy.LINEAR_WINS
        assert resolution.resolved_value == conflict.source_b

    def test_resolve_newest_wins(self):
        """Test newest_wins resolution strategy."""
        resolver = ConflictResolver(ConflictStrategy.NEWEST_WINS)
        
        conflict = Conflict(
            conflict_type=ConflictType.STATUS_MISMATCH,
            entity_type="track",
            entity_id="test_track",
            source_a={"status": "complete", "source": "git"},
            source_b={"status": "In Progress", "source": "linear"},
            source_a_updated="2026-02-23",
            source_b_updated="2026-02-22",  # Older
        )
        
        resolution = resolver.resolve_conflict(conflict)
        
        assert resolution.success is True
        assert resolution.strategy_used == ConflictStrategy.NEWEST_WINS
        # Source A is newer
        assert resolution.resolved_value == conflict.source_a

    def test_resolve_manual_review(self):
        """Test manual review flagging."""
        resolver = ConflictResolver(ConflictStrategy.MANUAL)
        
        conflict = Conflict(
            conflict_type=ConflictType.STATUS_MISMATCH,
            entity_type="track",
            entity_id="test_track",
            source_a={"status": "complete"},
            source_b={"status": "In Progress"},
            source_a_updated="2026-02-23",
            source_b_updated="2026-02-22",
        )
        
        resolution = resolver.resolve_conflict(conflict)
        
        assert resolution.success is False
        assert resolution.strategy_used == ConflictStrategy.MANUAL
        assert "manual review" in resolution.message.lower()

    def test_get_resolution_report(self):
        """Test resolution report generation."""
        resolver = ConflictResolver()
        
        # Create and resolve some conflicts
        conflict1 = Conflict(
            conflict_type=ConflictType.STATUS_MISMATCH,
            entity_type="track",
            entity_id="track1",
            source_a={"status": "complete"},
            source_b={"status": "done"},
            source_a_updated="2026-02-23",
            source_b_updated="2026-02-23",
        )
        
        resolver.resolve_conflict(conflict1)
        
        report = resolver.get_resolution_report()
        
        assert "total_conflicts" in report
        assert "resolved" in report
        assert "success_rate" in report
        assert report["total_conflicts"] >= 1

    def test_statuses_differ(self):
        """Test status comparison logic."""
        resolver = ConflictResolver()
        
        # Both complete = not different
        assert resolver._statuses_differ("complete", "done") is False
        assert resolver._statuses_differ("done", "closed") is False
        
        # One complete, one active = different
        assert resolver._statuses_differ("complete", "active") is True
        assert resolver._statuses_differ("done", "in_progress") is True
        
        # Both active = not different
        assert resolver._statuses_differ("active", "in_progress") is False

    def test_suggest_status_resolution(self):
        """Test automatic status resolution suggestions."""
        resolver = ConflictResolver()
        
        # Track complete, Linear done = no conflict
        track1 = {"status": "complete"}
        issue1 = {"state": {"name": "Done"}}
        assert resolver._suggest_status_resolution(track1, issue1) is None
        
        # Track complete, Linear not done = trust track
        track2 = {"status": "complete"}
        issue2 = {"state": {"name": "In Progress"}}
        suggestion = resolver._suggest_status_resolution(track2, issue2)
        assert suggestion == ConflictStrategy.GIT_WINS
        
        # Linear done, track not complete = trust Linear
        track3 = {"status": "active"}
        issue3 = {"state": {"name": "Done"}}
        suggestion = resolver._suggest_status_resolution(track3, issue3)
        assert suggestion == ConflictStrategy.LINEAR_WINS
