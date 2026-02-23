"""
Track Dependency Visualization

Generates visual dependency graphs for tracks using Mermaid.js format.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TrackNode:
    """Represents a track in the dependency graph."""
    id: str
    name: str
    status: str
    priority: str
    phase: int
    dependencies: List[str]
    dependents: List[str]


class DependencyGraph:
    """Generates dependency visualizations for tracks."""

    def __init__(self):
        """Initialize dependency graph generator."""
        self.tracks: Dict[str, TrackNode] = {}

    def add_track(self, track: Dict[str, Any]):
        """
        Add a track to the graph.

        Args:
            track: Track data dictionary
        """
        track_id = track.get("name", "")
        dependencies = track.get("metadata", {}).get("dependencies", [])
        
        self.tracks[track_id] = TrackNode(
            id=track_id,
            name=track.get("name", ""),
            status=track.get("status", "planning"),
            priority=track.get("metadata", {}).get("priority", "P2"),
            phase=track.get("metadata", {}).get("phase", 1),
            dependencies=dependencies,
            dependents=[],
        )

        # Update dependents for dependencies
        for dep_id in dependencies:
            if dep_id in self.tracks:
                self.tracks[dep_id].dependents.append(track_id)

    def build_from_tracks(self, tracks: List[Dict[str, Any]]):
        """
        Build graph from list of tracks.

        Args:
            tracks: List of track data dictionaries
        """
        for track in tracks:
            self.add_track(track)

    def generate_mermaid(self, layout: str = "TD") -> str:
        """
        Generate Mermaid.js diagram.

        Args:
            layout: Graph layout (TD, LR, RL, BT)

        Returns:
            Mermaid diagram string
        """
        lines = [f"graph {layout}", "    %% Track Dependencies", ""]

        # Define styles by status
        status_styles = {
            "complete": "fill:#22c55e,stroke:#15803d,color:#fff",
            "in_progress": "fill:#3b82f6,stroke:#1d4ed8,color:#fff",
            "active": "fill:#eab308,stroke:#a16207,color:#000",
            "planning": "fill:#6b7280,stroke:#374151,color:#fff",
            "archived": "fill:#9ca3af,stroke:#4b5563,color:#fff,stroke-dasharray: 5 5",
            "blocked": "fill:#ef4444,stroke:#b91c1c,color:#fff",
        }

        # Generate nodes
        for track_id, node in self.tracks.items():
            safe_id = self._safe_id(track_id)
            label = f"{node.name}\\n[{node.priority}] {node.status}"
            style = status_styles.get(node.status, status_styles["planning"])
            
            lines.append(f"    {safe_id}[\"{label}\"]")
            lines.append(f"    style {safe_id} {style}")

        lines.append("")

        # Generate edges
        for track_id, node in self.tracks.items():
            safe_id = self._safe_id(track_id)
            for dep_id in node.dependencies:
                if dep_id in self.tracks:
                    safe_dep = self._safe_id(dep_id)
                    lines.append(f"    {safe_dep} --> {safe_id}")

        return "\n".join(lines)

    def generate_mermaid_timeline(self) -> str:
        """
        Generate Mermaid timeline (gantt) view.

        Returns:
            Mermaid gantt diagram string
        """
        lines = [
            "gantt",
            "    Track Timeline",
            "    dateFormat  YYYY-MM-DD",
            "    axisFormat  %m/%d",
            "",
            "    section Phase 1",
        ]

        # Group tracks by phase
        phase_tracks: Dict[int, List[TrackNode]] = {}
        for node in self.tracks.values():
            phase = node.phase
            if phase not in phase_tracks:
                phase_tracks[phase] = []
            phase_tracks[phase].append(node)

        # Generate gantt bars
        for phase in sorted(phase_tracks.keys()):
            if phase > 1:
                lines.append(f"    section Phase {phase}")
            
            for node in phase_tracks[phase]:
                safe_id = self._safe_id(node.name)
                status = "done" if node.status == "complete" else "active"
                # Placeholder dates - would be calculated from actual track data
                lines.append(f"    {node.name} :{status}, {safe_id}, 2026-02-23, 5d")

        return "\n".join(lines)

    def generate_mermaid_flowchart(self) -> str:
        """
        Generate detailed flowchart with dependency types.

        Returns:
            Mermaid flowchart string
        """
        lines = [
            "flowchart TD",
            "    %% Track Dependency Flowchart",
            "",
            "    %% Subgraphs by Phase",
        ]

        # Group by phase
        phase_tracks: Dict[int, List[TrackNode]] = {}
        for node in self.tracks.values():
            phase = node.phase
            if phase not in phase_tracks:
                phase_tracks[phase] = []
            phase_tracks[phase].append(node)

        for phase in sorted(phase_tracks.keys()):
            lines.append(f"    subgraph Phase{phase}[Phase {phase}]")
            for node in phase_tracks[phase]:
                safe_id = self._safe_id(node.name)
                lines.append(f"        {safe_id}[{node.name}]")
            lines.append("    end")

        lines.append("")
        lines.append("    %% Dependencies")

        # Add dependency edges with labels
        for track_id, node in self.tracks.items():
            safe_id = self._safe_id(track_id)
            for dep_id in node.dependencies:
                if dep_id in self.tracks:
                    safe_dep = self._safe_id(dep_id)
                    lines.append(f"    {safe_dep} -->|depends on| {safe_id}")

        return "\n".join(lines)

    def find_critical_path(self) -> List[str]:
        """
        Find the critical path (longest dependency chain).

        Returns:
            List of track IDs in the critical path
        """
        # Topological sort with path tracking
        visited = set()
        path = []
        critical_path = []

        def dfs(track_id: str) -> int:
            if track_id in visited:
                return 0
            
            visited.add(track_id)
            node = self.tracks.get(track_id)
            
            if not node:
                return 0

            max_depth = 0
            for dep_id in node.dependencies:
                depth = dfs(dep_id)
                if depth > max_depth:
                    max_depth = depth

            current_path = path + [track_id]
            if len(current_path) > len(critical_path):
                critical_path.clear()
                critical_path.extend(current_path)

            return max_depth + 1

        for track_id in self.tracks:
            dfs(track_id)

        return critical_path

    def find_blockers(self) -> List[Dict[str, Any]]:
        """
        Find tracks that are blocking others.

        Returns:
            List of blocker information
        """
        blockers = []

        for track_id, node in self.tracks.items():
            if node.status not in ["complete", "done"]:
                if node.dependents:
                    blockers.append({
                        "track_id": track_id,
                        "track_name": node.name,
                        "status": node.status,
                        "blocking": node.dependents,
                        "blocking_count": len(node.dependents),
                    })

        # Sort by number of blocked tracks
        blockers.sort(key=lambda x: x["blocking_count"], reverse=True)
        return blockers

    def get_dependency_stats(self) -> Dict[str, Any]:
        """
        Get dependency statistics.

        Returns:
            Statistics dictionary
        """
        total_tracks = len(self.tracks)
        total_deps = sum(len(node.dependencies) for node in self.tracks.values())
        
        # Find tracks with no dependencies
        independent = [
            tid for tid, node in self.tracks.items()
            if not node.dependencies
        ]
        
        # Find tracks with most dependencies
        most_deps = max(
            self.tracks.items(),
            key=lambda x: len(x[1].dependencies),
            default=(None, None)
        )

        return {
            "total_tracks": total_tracks,
            "total_dependencies": total_deps,
            "average_deps_per_track": total_deps / total_tracks if total_tracks > 0 else 0,
            "independent_tracks": len(independent),
            "most_dependencies": {
                "track": most_deps[0],
                "count": len(most_deps[1].dependencies) if most_deps[1] else 0,
            },
            "critical_path_length": len(self.find_critical_path()),
            "blockers_count": len(self.find_blockers()),
        }

    def _safe_id(self, track_id: str) -> str:
        """Convert track ID to safe Mermaid identifier."""
        # Replace special characters
        safe = track_id.replace("-", "_").replace(" ", "_").replace("/", "_")
        # Ensure starts with letter
        if safe and safe[0].isdigit():
            safe = "t_" + safe
        return safe

    def generate_markdown_report(self) -> str:
        """
        Generate a markdown report with embedded Mermaid diagrams.

        Returns:
            Markdown report string
        """
        stats = self.get_dependency_stats()
        blockers = self.find_blockers()
        critical_path = self.find_critical_path()

        lines = [
            "# Track Dependency Report",
            "",
            "## Summary",
            "",
            f"- **Total Tracks**: {stats['total_tracks']}",
            f"- **Total Dependencies**: {stats['total_dependencies']}",
            f"- **Average Dependencies**: {stats['average_deps_per_track']:.1f}",
            f"- **Independent Tracks**: {stats['independent_tracks']}",
            f"- **Critical Path Length**: {stats['critical_path_length']}",
            f"- **Active Blockers**: {stats['blockers_count']}",
            "",
            "## Dependency Graph",
            "",
            "```mermaid",
            self.generate_mermaid(),
            "```",
            "",
        ]

        if blockers:
            lines.extend([
                "## ⚠️ Blockers",
                "",
                "These tracks are blocking others:",
                "",
            ])
            for blocker in blockers[:5]:  # Top 5
                lines.append(
                    f"- **{blocker['track_name']}** ({blocker['status']}) "
                    f"- blocking {blocker['blocking_count']} tracks"
                )
            lines.append("")

        if critical_path:
            lines.extend([
                "## Critical Path",
                "",
                "Longest dependency chain:",
                "",
                " → ".join(critical_path),
                "",
            ])

        return "\n".join(lines)


def generate_dependency_visualization(tracks: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
    """
    Generate dependency visualization for tracks.

    Args:
        tracks: List of track data
        output_file: Optional file to write report to

    Returns:
        Generated report string
    """
    graph = DependencyGraph()
    graph.build_from_tracks(tracks)
    
    report = graph.generate_markdown_report()
    
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
        logger.info(f"Dependency report written to {output_file}")
    
    return report
