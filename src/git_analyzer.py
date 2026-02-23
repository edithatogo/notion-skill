"""
Git Repository Analyzer

Analyzes Git repositories to extract:
- Commit history
- Branch information
- Repository metadata
- Recent activity
"""

import os
import logging
from typing import Dict, List, Any, Optional
from git import Repo
from datetime import datetime

logger = logging.getLogger(__name__)


class GitAnalyzer:
    """Analyzer for Git repositories."""

    def __init__(self, repo_path: str = "."):
        """
        Initialize Git analyzer.

        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = os.path.abspath(repo_path)
        self.repo = None
        self._load_repo()

    def _load_repo(self):
        """Load the Git repository."""
        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Loaded repository: {self.repo_path}")
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            raise

    def get_repository_metadata(self) -> Dict[str, Any]:
        """
        Get repository metadata.

        Returns:
            Dictionary with repository information
        """
        if not self.repo:
            return {}

        try:
            # Get primary language (from file extensions)
            languages = self._get_languages()
            primary_language = max(languages.items(), key=lambda x: x[1])[0] if languages else "Unknown"

            # Get latest commit info
            latest_commit = self.repo.head.commit if self.repo.heads else None

            return {
                "name": self.repo.name,
                "path": self.repo_path,
                "primary_language": primary_language,
                "languages": languages,
                "branch_count": len(self.repo.branches),
                "commit_count": len(list(self.repo.iter_commits())),
                "last_commit_date": latest_commit.committed_datetime.isoformat() if latest_commit else None,
                "last_commit_author": str(latest_commit.author) if latest_commit else None,
                "last_commit_message": latest_commit.message.strip() if latest_commit else None,
                "last_commit_sha": latest_commit.hexsha if latest_commit else None,
                "has_conductor": self._has_conductor_folder(),
            }
        except Exception as e:
            logger.error(f"Failed to get repository metadata: {e}")
            return {}

    def _get_languages(self) -> Dict[str, int]:
        """
        Get language statistics for the repository.

        Returns:
            Dictionary mapping language to file count
        """
        languages = {}
        language_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C",
            ".cs": "C#",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".sh": "Shell",
            ".bash": "Shell",
        }

        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "venv", "__pycache__", "dist", "build"]]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in language_extensions:
                    lang = language_extensions[ext]
                    languages[lang] = languages.get(lang, 0) + 1

        return languages

    def _has_conductor_folder(self) -> bool:
        """Check if repository has a conductor folder."""
        conductor_path = os.path.join(self.repo_path, "conductor")
        return os.path.isdir(conductor_path)

    def get_recent_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commits.

        Args:
            limit: Maximum number of commits to return

        Returns:
            List of commit information
        """
        if not self.repo:
            return []

        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    "sha": commit.hexsha,
                    "author": str(commit.author),
                    "email": commit.author.email,
                    "message": commit.message.strip(),
                    "date": commit.committed_datetime.isoformat(),
                    "files_changed": len(commit.stats.files),
                    "insertions": commit.stats.total.get("insertions", 0),
                    "deletions": commit.stats.total.get("deletions", 0),
                })
            return commits
        except Exception as e:
            logger.error(f"Failed to get recent commits: {e}")
            return []

    def get_branches(self) -> List[Dict[str, Any]]:
        """
        Get all branches.

        Returns:
            List of branch information
        """
        if not self.repo:
            return []

        branches = []
        for branch in self.repo.branches:
            branches.append({
                "name": branch.name,
                "is_current": branch == self.repo.active_branch,
                "commit_sha": branch.commit.hexsha,
                "commit_date": branch.commit.committed_datetime.isoformat(),
            })
        return branches

    def get_commit_history_for_track(self, track_name: str) -> List[Dict[str, Any]]:
        """
        Get commits related to a specific track.

        Args:
            track_name: Name of the track

        Returns:
            List of related commits
        """
        if not self.repo:
            return []

        try:
            # Search for commits mentioning the track name
            related_commits = []
            for commit in self.repo.iter_commits():
                if track_name.lower() in commit.message.lower():
                    related_commits.append({
                        "sha": commit.hexsha,
                        "author": str(commit.author),
                        "message": commit.message.strip(),
                        "date": commit.committed_datetime.isoformat(),
                    })
            return related_commits
        except Exception as e:
            logger.error(f"Failed to get commit history for track: {e}")
            return []
