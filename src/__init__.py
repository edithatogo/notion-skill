"""
Notion Skill - Repository Reflection & Linear Integration

This package provides tools for syncing repository structure,
conductor tracks, and Linear project data to Notion databases.

Version 1.2.0 - All improvements implemented
"""

__version__ = "1.2.0"
__author__ = "Notion Integration Team"

# Core clients
from .notion_client import NotionClient
from .linear_client import LinearClient

# Analysis modules
from .git_analyzer import GitAnalyzer
from .track_parser import TrackParser

# Sync engine
from .sync_engine import SyncEngine

# Incremental sync
from .incremental_sync import IncrementalSyncManager, SyncState, ChangeSet

# Bidirectional sync
from .bidirectional_sync import BidirectionalSync

# Conflict resolution
from .conflict_resolution import ConflictResolver, ConflictStrategy, ConflictType, Conflict

# Error recovery
from .error_recovery import ErrorRecoveryManager, ErrorType, RetryStrategy, with_retry

# Templates
from .notion_templates import get_template, get_all_templates, create_database_payload

# Metrics
from .sync_metrics import MetricsCollector, SyncMetrics

# MCP server
from .mcp_server import NotionSkillMCPServer, create_mcp_server

# Webhook server
from .webhook_server import WebhookServer, create_webhook_server, LinearWebhookHandler, NotionWebhookHandler

# Dependency visualization
from .dependency_visualization import DependencyGraph, generate_dependency_visualization

# Multi-workspace
from .multi_workspace import WorkspaceManager, WorkspaceConfig

__all__ = [
    # Core clients
    "NotionClient",
    "LinearClient",
    "GitAnalyzer",
    "TrackParser",
    "SyncEngine",
    
    # Incremental sync
    "IncrementalSyncManager",
    "SyncState",
    "ChangeSet",
    
    # Bidirectional sync
    "BidirectionalSync",
    
    # Conflict resolution
    "ConflictResolver",
    "ConflictStrategy",
    "ConflictType",
    "Conflict",
    
    # Error recovery
    "ErrorRecoveryManager",
    "ErrorType",
    "RetryStrategy",
    "with_retry",
    
    # Templates
    "get_template",
    "get_all_templates",
    "create_database_payload",
    
    # Metrics
    "MetricsCollector",
    "SyncMetrics",
    
    # MCP server
    "NotionSkillMCPServer",
    "create_mcp_server",
    
    # Webhook server
    "WebhookServer",
    "create_webhook_server",
    "LinearWebhookHandler",
    "NotionWebhookHandler",
    
    # Dependency visualization
    "DependencyGraph",
    "generate_dependency_visualization",
    
    # Multi-workspace
    "WorkspaceManager",
    "WorkspaceConfig",
]
