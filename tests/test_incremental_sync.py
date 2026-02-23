"""
Tests for Incremental Sync Module
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.incremental_sync import (
    IncrementalSyncManager,
    SyncState,
    ChangeSet,
)


class TestIncrementalSyncManager:
    """Tests for IncrementalSyncManager."""

    def test_init_default_cache_dir(self, tmp_path):
        """Test initialization with default cache directory."""
        manager = IncrementalSyncManager(str(tmp_path))
        assert manager.cache_dir == tmp_path

    def test_compute_track_hash(self):
        """Test track hash computation."""
        manager = IncrementalSyncManager()
        
        track1 = {
            "name": "test_track_20260223",
            "status": "complete",
            "commit_sha": "abc123",
            "completed_date": "2026-02-23",
            "metadata": {"priority": "P0"},
        }
        
        track2 = {
            "name": "test_track_20260223",
            "status": "complete",
            "commit_sha": "abc123",
            "completed_date": "2026-02-23",
            "metadata": {"priority": "P0"},
        }
        
        track3 = {
            "name": "test_track_20260223",
            "status": "active",  # Different status
            "commit_sha": "abc123",
            "completed_date": "2026-02-23",
            "metadata": {"priority": "P0"},
        }
        
        hash1 = manager._compute_track_hash(track1)
        hash2 = manager._compute_track_hash(track2)
        hash3 = manager._compute_track_hash(track3)
        
        # Same data should produce same hash
        assert hash1 == hash2
        
        # Different data should produce different hash
        assert hash1 != hash3

    def test_compute_issue_hash(self):
        """Test Linear issue hash computation."""
        manager = IncrementalSyncManager()
        
        issue1 = {
            "id": "EDI-25",
            "title": "Test Issue",
            "state": {"name": "Done"},
            "priority": 2,
            "assignee": {"id": "user123"},
            "completedAt": "2026-02-23",
        }
        
        issue2 = {
            "id": "EDI-25",
            "title": "Test Issue",
            "state": {"name": "Done"},
            "priority": 2,
            "assignee": {"id": "user123"},
            "completedAt": "2026-02-23",
        }
        
        issue3 = {
            "id": "EDI-25",
            "title": "Test Issue",
            "state": {"name": "In Progress"},  # Different state
            "priority": 2,
            "assignee": {"id": "user123"},
            "completedAt": "2026-02-23",
        }
        
        hash1 = manager._compute_issue_hash(issue1)
        hash2 = manager._compute_issue_hash(issue2)
        hash3 = manager._compute_issue_hash(issue3)
        
        assert hash1 == hash2
        assert hash1 != hash3

    def test_detect_changes_first_sync(self, tmp_path):
        """Test change detection for first sync."""
        manager = IncrementalSyncManager(str(tmp_path))
        
        tracks = [
            {"name": "track1", "status": "complete"},
            {"name": "track2", "status": "active"},
        ]
        
        commits = [
            {"sha": "abc123", "message": "Test commit"},
        ]
        
        changes = manager.detect_changes(
            repo_path=str(tmp_path),
            current_tracks=tracks,
            current_commits=commits,
        )
        
        assert changes.has_changes is True
        assert len(changes.new_tracks) == 2
        assert "Initial sync" in changes.summary

    def test_detect_changes_no_changes(self, tmp_path):
        """Test change detection when nothing changed."""
        manager = IncrementalSyncManager(str(tmp_path))
        
        tracks = [
            {"name": "track1", "status": "complete"},
        ]
        
        commits = [
            {"sha": "abc123", "message": "Test commit"},
        ]
        
        # First sync to establish baseline
        manager.detect_changes(
            repo_path=str(tmp_path),
            current_tracks=tracks,
            current_commits=commits,
        )
        
        # Save state
        state = manager.create_sync_state(
            repo_path=str(tmp_path),
            tracks=tracks,
            commits=commits,
        )
        manager.save_sync_state(str(tmp_path), state)
        
        # Second sync with same data
        changes = manager.detect_changes(
            repo_path=str(tmp_path),
            current_tracks=tracks,
            current_commits=commits,
        )
        
        assert changes.has_changes is False
        assert "No changes" in changes.summary

    def test_detect_changes_new_track(self, tmp_path):
        """Test change detection for new track."""
        manager = IncrementalSyncManager(str(tmp_path))
        
        # Initial state
        initial_tracks = [
            {"name": "track1", "status": "complete"},
        ]
        
        # New state with additional track
        new_tracks = [
            {"name": "track1", "status": "complete"},
            {"name": "track2", "status": "active"},  # New
        ]
        
        commits = [{"sha": "abc123", "message": "Test"}]
        
        # Establish baseline
        state = manager.create_sync_state(
            repo_path=str(tmp_path),
            tracks=initial_tracks,
            commits=commits,
        )
        manager.save_sync_state(str(tmp_path), state)
        
        # Detect changes
        changes = manager.detect_changes(
            repo_path=str(tmp_path),
            current_tracks=new_tracks,
            current_commits=commits,
        )
        
        assert changes.has_changes is True
        assert len(changes.new_tracks) == 1
        assert changes.new_tracks[0]["name"] == "track2"

    def test_should_skip_sync_no_changes(self):
        """Test sync skip when no changes."""
        manager = IncrementalSyncManager()
        
        changes = ChangeSet(
            has_changes=False,
            new_tracks=[],
            updated_tracks=[],
            deleted_tracks=[],
            new_commits=[],
            linear_issues_changed=False,
            linear_new_issues=[],
            linear_updated_issues=[],
            metadata_changed=False,
            summary="No changes detected",
        )
        
        config = {}
        should_skip, reason = manager.should_skip_sync(changes, config)
        
        assert should_skip is True
        assert "No changes" in reason

    def test_get_sync_preview(self):
        """Test sync preview generation."""
        manager = IncrementalSyncManager()
        
        changes = ChangeSet(
            has_changes=True,
            new_tracks=[{"name": "new_track", "status": "active"}],
            updated_tracks=[],
            deleted_tracks=[],
            new_commits=[{"sha": "abc123", "message": "Test commit"}],
            linear_issues_changed=False,
            linear_new_issues=[],
            linear_updated_issues=[],
            metadata_changed=False,
            summary="1 new track; 1 new commit",
        )
        
        preview = manager.get_sync_preview(changes)
        
        assert "Sync Preview" in preview
        assert "New Tracks" in preview
        assert "new_track" in preview
        assert "abc123" in preview


class TestSyncState:
    """Tests for SyncState dataclass."""

    def test_create_sync_state(self):
        """Test SyncState creation."""
        tracks = [{"name": "track1", "status": "complete"}]
        commits = [{"sha": "abc123"}]
        
        manager = IncrementalSyncManager()
        state = manager.create_sync_state(
            repo_path="/test/repo",
            tracks=tracks,
            commits=commits,
            linear_project_id="project123",
        )
        
        assert state.repo_path == "/test/repo"
        assert state.last_commit_sha == "abc123"
        assert state.linear_project_id == "project123"
        assert len(state.track_hashes) == 1

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading sync state."""
        manager = IncrementalSyncManager(str(tmp_path))
        
        tracks = [{"name": "track1", "status": "complete"}]
        commits = [{"sha": "abc123"}]
        
        state = manager.create_sync_state(
            repo_path=str(tmp_path),
            tracks=tracks,
            commits=commits,
        )
        
        # Save
        manager.save_sync_state(str(tmp_path), state)
        
        # Load
        loaded = manager.load_last_sync_state(str(tmp_path))
        
        assert loaded is not None
        assert loaded.repo_path == state.repo_path
        assert loaded.last_commit_sha == state.last_commit_sha
