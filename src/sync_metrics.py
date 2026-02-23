"""
Sync Metrics & Dashboards

Collects and reports metrics about sync operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


@dataclass
class SyncMetrics:
    """Metrics for a single sync operation."""
    sync_id: str
    repository: str
    timestamp: str
    duration_ms: int
    items_synced: int
    api_calls_made: int
    rate_limit_hits: int
    errors_count: int
    success_rate: float
    sync_mode: str  # "full", "incremental", "preview"
    changes_detected: str
    skipped: bool
    skip_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates sync metrics."""

    def __init__(self, metrics_dir: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory to store metrics. Defaults to .notion-metrics
        """
        self.metrics_dir = Path(metrics_dir) if metrics_dir else Path(".notion-metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "sync_metrics.json"
        self.current_metrics: List[SyncMetrics] = []
        self._load_metrics()

    def record_sync(self, metrics: SyncMetrics):
        """
        Record metrics from a sync operation.

        Args:
            metrics: SyncMetrics object
        """
        self.current_metrics.append(metrics)
        self._save_metrics()
        logger.debug(f"Recorded sync metrics: {metrics.sync_id}")

    def _save_metrics(self):
        """Save metrics to disk."""
        try:
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump([asdict(m) for m in self.current_metrics], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _load_metrics(self):
        """Load metrics from disk."""
        if not self.metrics_file.exists():
            return

        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_metrics = [SyncMetrics(**m) for m in data]
            logger.info(f"Loaded {len(self.current_metrics)} sync metrics")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for recent syncs.

        Args:
            days: Number of days to include

        Returns:
            Summary statistics
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            m for m in self.current_metrics
            if datetime.fromisoformat(m.timestamp) >= cutoff
        ]

        if not recent:
            return {"message": "No syncs in the last {} days".format(days)}

        # Calculate statistics
        durations = [m.duration_ms for m in recent]
        items_synced = [m.items_synced for m in recent]
        api_calls = [m.api_calls_made for m in recent]
        success_rates = [m.success_rate for m in recent]

        # Count by sync mode
        by_mode = {}
        for m in recent:
            by_mode[m.sync_mode] = by_mode.get(m.sync_mode, 0) + 1

        # Count skipped syncs
        skipped_count = sum(1 for m in recent if m.skipped)

        # Error rate
        total_errors = sum(m.errors_count for m in recent)
        total_items = sum(m.items_synced for m in recent)

        return {
            "period_days": days,
            "total_syncs": len(recent),
            "successful_syncs": sum(1 for m in recent if m.success_rate == 1.0),
            "skipped_syncs": skipped_count,
            "sync_modes": by_mode,
            "duration": {
                "mean_ms": mean(durations),
                "median_ms": median(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "std_dev_ms": stdev(durations) if len(durations) > 1 else 0,
            },
            "items_synced": {
                "total": sum(items_synced),
                "mean": mean(items_synced),
                "median": median(items_synced),
            },
            "api_calls": {
                "total": sum(api_calls),
                "mean": mean(api_calls),
                "per_item_ratio": sum(api_calls) / sum(items_synced) if sum(items_synced) > 0 else 0,
            },
            "success_rate": {
                "mean": mean(success_rates),
                "min": min(success_rates),
            },
            "error_rate": total_errors / total_items if total_items > 0 else 0,
            "rate_limit_hits": sum(m.rate_limit_hits for m in recent),
        }

    def get_repository_stats(self, repo_path: str) -> Dict[str, Any]:
        """
        Get statistics for a specific repository.

        Args:
            repo_path: Path to the repository

        Returns:
            Repository statistics
        """
        repo_metrics = [m for m in self.current_metrics if m.repository == repo_path]

        if not repo_metrics:
            return {"message": "No syncs found for this repository"}

        # Sort by timestamp
        repo_metrics.sort(key=lambda m: m.timestamp, reverse=True)

        last_sync = repo_metrics[0] if repo_metrics else None

        return {
            "repository": repo_path,
            "total_syncs": len(repo_metrics),
            "last_sync": asdict(last_sync) if last_sync else None,
            "average_duration_ms": mean([m.duration_ms for m in repo_metrics]),
            "total_items_synced": sum([m.items_synced for m in repo_metrics]),
            "total_api_calls": sum([m.api_calls_made for m in repo_metrics]),
            "error_count": sum([m.errors_count for m in repo_metrics]),
        }

    def generate_dashboard_markdown(self) -> str:
        """
        Generate a markdown dashboard for display in Notion or README.

        Returns:
            Markdown string
        """
        summary = self.get_summary(days=30)
        top_repos = self._get_top_repositories(limit=5)

        lines = [
            "# 📊 Sync Metrics Dashboard",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "## Last 30 Days Summary",
            "",
            f"- **Total Syncs**: {summary.get('total_syncs', 0)}",
            f"- **Successful**: {summary.get('successful_syncs', 0)}",
            f"- **Skipped**: {summary.get('skipped_syncs', 0)}",
            f"- **Mean Duration**: {summary.get('duration', {}).get('mean_ms', 0):.0f}ms",
            f"- **Mean Success Rate**: {summary.get('success_rate', {}).get('mean', 0):.1%}",
            "",
            "## Sync Modes",
            "",
        ]

        for mode, count in summary.get('sync_modes', {}).items():
            lines.append(f"- {mode.title()}: {count}")

        lines.extend([
            "",
            "## Top Repositories",
            "",
            "| Repository | Syncs | Items | Avg Duration |",
            "|------------|-------|-------|--------------|",
        ])

        for repo in top_repos:
            lines.append(
                f"| {repo['repository']} | {repo['total_syncs']} | "
                f"{repo['total_items_synced']} | {repo['average_duration_ms']:.0f}ms |"
            )

        lines.extend([
            "",
            "## Recent Syncs",
            "",
            "| Time | Repository | Mode | Duration | Items | Status |",
            "|------|------------|------|----------|-------|--------|",
        ])

        recent = self.current_metrics[-10:]  # Last 10
        for m in recent:
            status_icon = "✅" if m.success_rate == 1.0 else "❌"
            time_str = datetime.fromisoformat(m.timestamp).strftime('%m-%d %H:%M')
            lines.append(
                f"| {time_str} | {Path(m.repository).name} | {m.sync_mode} | "
                f"{m.duration_ms}ms | {m.items_synced} | {status_icon} |"
            )

        return "\n".join(lines)

    def _get_top_repositories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top repositories by sync count."""
        repo_counts = {}
        for m in self.current_metrics:
            repo = m.repository
            if repo not in repo_counts:
                repo_counts[repo] = {
                    "repository": repo,
                    "total_syncs": 0,
                    "total_items_synced": 0,
                    "total_duration_ms": 0,
                }
            repo_counts[repo]["total_syncs"] += 1
            repo_counts[repo]["total_items_synced"] += m.items_synced
            repo_counts[repo]["total_duration_ms"] += m.duration_ms

        # Calculate averages
        for repo in repo_counts.values():
            repo["average_duration_ms"] = repo["total_duration_ms"] / repo["total_syncs"]

        # Sort by sync count
        sorted_repos = sorted(
            repo_counts.values(),
            key=lambda x: x["total_syncs"],
            reverse=True
        )

        return sorted_repos[:limit]

    def export_metrics(self, output_file: str, format: str = "json"):
        """
        Export metrics to a file.

        Args:
            output_file: Path to output file
            format: Export format ("json" or "csv")
        """
        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([asdict(m) for m in self.current_metrics], f, indent=2)
        elif format == "csv":
            import csv
            if self.current_metrics:
                with open(output_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=asdict(self.current_metrics[0]).keys())
                    writer.writeheader()
                    for m in self.current_metrics:
                        writer.writerow(asdict(m))
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Exported {len(self.current_metrics)} metrics to {output_file}")

    def clear_old_metrics(self, days: int = 90):
        """
        Clear metrics older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.current_metrics)

        self.current_metrics = [
            m for m in self.current_metrics
            if datetime.fromisoformat(m.timestamp) >= cutoff
        ]

        removed = original_count - len(self.current_metrics)
        self._save_metrics()

        if removed > 0:
            logger.info(f"Removed {removed} metrics older than {days} days")
