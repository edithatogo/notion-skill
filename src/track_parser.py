"""
Conductor Track Parser

Parses conductor/tracks.md files to extract:
- Track names and status
- Commit SHAs
- Track metadata
- Dependencies and relationships
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TrackParser:
    """Parser for conductor track files."""

    # Regex patterns for parsing tracks
    STATUS_PATTERNS = {
        "complete": r"\[x\]",
        "in_progress": r"\[~\]",
        "active": r"\[ \]",
        "planning": r"(?<!\[)(?<!\[x)(?<!\[~)-",
    }

    COMMIT_SHA_PATTERN = r"\[([a-f0-9]{7,40})\]"
    TRACK_NAME_PATTERN = r"(?:\[.\]\s*)?([a-zA-Z0-9_-]+_\d{8}|[a-zA-Z0-9_-]+)"
    DATE_PATTERN = r"_(\d{8})"

    def __init__(self, repo_path: str):
        """
        Initialize track parser.

        Args:
            repo_path: Path to the repository
        """
        self.repo_path = Path(repo_path)
        self.tracks_file = self.repo_path / "conductor" / "tracks.md"
        self.tracks_archive = self.repo_path / "conductor" / "tracks" / "archive"

    def parse_tracks_file(self) -> List[Dict[str, Any]]:
        """
        Parse the main tracks.md file.

        Returns:
            List of track dictionaries
        """
        if not self.tracks_file.exists():
            logger.warning(f"Tracks file not found: {self.tracks_file}")
            return []

        try:
            content = self.tracks_file.read_text(encoding="utf-8")
            tracks = []

            # Parse completed tracks
            completed_section = self._extract_section(content, "Completed Tracks")
            if completed_section:
                tracks.extend(self._parse_track_lines(completed_section, "complete"))

            # Parse active tracks
            active_section = self._extract_section(content, "Active Tracks")
            if active_section:
                tracks.extend(self._parse_track_lines(active_section, "active"))

            # Parse archived tracks
            archived_section = self._extract_section(content, "Archived Tracks")
            if archived_section:
                tracks.extend(self._parse_track_lines(archived_section, "archived"))

            logger.info(f"Parsed {len(tracks)} tracks from {self.tracks_file}")
            return tracks

        except Exception as e:
            logger.error(f"Failed to parse tracks file: {e}")
            return []

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a section from the tracks file."""
        pattern = rf"##.*?{re.escape(section_name)}.*?(?=##|$)"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        return match.group(0) if match else None

    def _parse_track_lines(self, section: str, default_status: str) -> List[Dict[str, Any]]:
        """Parse track lines from a section."""
        tracks = []
        lines = section.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Determine status
            status = default_status
            if re.search(self.STATUS_PATTERNS["complete"], line):
                status = "complete"
            elif re.search(self.STATUS_PATTERNS["in_progress"], line):
                status = "in_progress"
            elif re.search(self.STATUS_PATTERNS["active"], line):
                status = "active"

            # Extract track name
            name_match = re.search(self.TRACK_NAME_PATTERN, line)
            if not name_match:
                continue

            track_name = name_match.group(1).strip()

            # Extract commit SHA
            sha_match = re.search(self.COMMIT_SHA_PATTERN, line)
            commit_sha = sha_match.group(1) if sha_match else None

            # Extract date from track name
            date_match = re.search(self.DATE_PATTERN, track_name)
            completed_date = None
            if date_match:
                try:
                    date_str = date_match.group(1)
                    completed_date = datetime.strptime(date_str, "%Y%m%d").isoformat()
                except ValueError:
                    pass

            # Try to get metadata from archive
            metadata = self._get_track_metadata(track_name)

            tracks.append({
                "name": track_name,
                "status": status,
                "commit_sha": commit_sha,
                "completed_date": completed_date,
                "metadata": metadata,
                "archive_path": str(self.tracks_archive / track_name) if os.path.isdir(self.tracks_archive / track_name) else None,
            })

        return tracks

    def _get_track_metadata(self, track_name: str) -> Dict[str, Any]:
        """Get metadata for a track from its archive folder."""
        metadata_file = self.tracks_archive / track_name / "metadata.json"

        if not metadata_file.exists():
            return {}

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata for {track_name}: {e}")
            return {}

    def parse_all_archived_tracks(self) -> List[Dict[str, Any]]:
        """
        Parse all archived tracks.

        Returns:
            List of all archived track information
        """
        if not self.tracks_archive.exists():
            return []

        tracks = []
        for track_dir in self.tracks_archive.iterdir():
            if not track_dir.is_dir():
                continue

            track_name = track_dir.name
            metadata = self._get_track_metadata(track_name)

            # Try to get status from tracks.md
            all_tracks = self.parse_tracks_file()
            track_info = next((t for t in all_tracks if t["name"] == track_name), None)

            tracks.append({
                "name": track_name,
                "status": "complete" if track_info and track_info["status"] == "complete" else "archived",
                "commit_sha": track_info.get("commit_sha") if track_info else None,
                "completed_date": track_info.get("completed_date") if track_info else None,
                "metadata": metadata,
                "archive_path": str(track_dir),
                "has_spec": (track_dir / "spec.md").exists(),
                "has_plan": (track_dir / "plan.md").exists(),
                "has_metadata": (track_dir / "metadata.json").exists(),
            })

        return tracks

    def get_track_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tracks.

        Returns:
            Dictionary with track statistics
        """
        tracks = self.parse_tracks_file()
        archived = self.parse_all_archived_tracks()

        all_tracks = tracks + archived

        status_counts = {}
        for track in all_tracks:
            status = track.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tracks": len(all_tracks),
            "status_counts": status_counts,
            "completed_tracks": status_counts.get("complete", 0),
            "active_tracks": status_counts.get("active", 0) + status_counts.get("in_progress", 0),
            "archived_tracks": len(archived),
            "tracks_with_metadata": sum(1 for t in archived if t.get("metadata")),
            "tracks_with_spec": sum(1 for t in archived if t.get("has_spec")),
            "tracks_with_plan": sum(1 for t in archived if t.get("has_plan")),
        }

    def find_track_by_name(self, track_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific track by name.

        Args:
            track_name: Name of the track to find

        Returns:
            Track information or None
        """
        all_tracks = self.parse_tracks_file() + self.parse_all_archived_tracks()
        return next((t for t in all_tracks if t["name"] == track_name), None)

    def get_tracks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all tracks with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of matching tracks
        """
        all_tracks = self.parse_tracks_file() + self.parse_all_archived_tracks()
        return [t for t in all_tracks if t.get("status") == status]
