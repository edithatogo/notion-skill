"""
Multi-Workspace Support

Manages synchronization across multiple Notion workspaces.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceConfig:
    """Configuration for a Notion workspace."""
    name: str
    api_key: str
    workspace_id: str
    databases: Dict[str, str]  # database_name -> database_id
    default: bool = False
    enabled: bool = True


class WorkspaceManager:
    """Manages multiple Notion workspaces."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize workspace manager.

        Args:
            config_file: Path to workspace configuration file
        """
        self.config_file = config_file or self._default_config_path()
        self.workspaces: Dict[str, WorkspaceConfig] = {}
        self.current_workspace: Optional[str] = None
        
        # Load configuration
        if Path(self.config_file).exists():
            self.load_config()
        else:
            # Initialize with environment variables
            self._init_from_env()

    def _default_config_path(self) -> str:
        """Get default config file path."""
        return str(Path.home() / ".notion-skill" / "workspaces.json")

    def _init_from_env(self):
        """Initialize workspace from environment variables."""
        api_key = os.getenv("NOTION_API_KEY")
        workspace_id = os.getenv("NOTION_WORKSPACE_ID", "default")
        
        if api_key:
            self.add_workspace(
                name="default",
                api_key=api_key,
                workspace_id=workspace_id,
                databases={
                    "repositories": os.getenv("NOTION_REPOSITORIES_DB_ID", ""),
                    "tracks": os.getenv("NOTION_TRACKS_DB_ID", ""),
                    "linear_projects": os.getenv("NOTION_LINEAR_PROJECTS_DB_ID", ""),
                },
                default=True,
            )

    def load_config(self):
        """Load workspace configuration from file."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for name, ws_data in data.get("workspaces", {}).items():
                self.workspaces[name] = WorkspaceConfig(
                    name=name,
                    api_key=ws_data.get("api_key", ""),
                    workspace_id=ws_data.get("workspace_id", ""),
                    databases=ws_data.get("databases", {}),
                    default=ws_data.get("default", False),
                    enabled=ws_data.get("enabled", True),
                )
            
            self.current_workspace = data.get("current_workspace")
            
            # Set default if none selected
            if not self.current_workspace:
                for name, ws in self.workspaces.items():
                    if ws.default:
                        self.current_workspace = name
                        break
            
            logger.info(f"Loaded {len(self.workspaces)} workspaces")
            
        except Exception as e:
            logger.error(f"Failed to load workspace config: {e}")

    def save_config(self):
        """Save workspace configuration to file."""
        try:
            # Ensure directory exists
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "current_workspace": self.current_workspace,
                "workspaces": {
                    name: asdict(ws)
                    for name, ws in self.workspaces.items()
                }
            }
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved workspace config to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save workspace config: {e}")

    def add_workspace(
        self,
        name: str,
        api_key: str,
        workspace_id: str,
        databases: Dict[str, str],
        default: bool = False,
        enabled: bool = True,
    ):
        """
        Add a new workspace.

        Args:
            name: Workspace name
            api_key: Notion API key
            workspace_id: Notion workspace ID
            databases: Database ID mappings
            default: Whether this is the default workspace
            enabled: Whether this workspace is enabled
        """
        if default:
            # Unset other defaults
            for ws in self.workspaces.values():
                ws.default = False
        
        self.workspaces[name] = WorkspaceConfig(
            name=name,
            api_key=api_key,
            workspace_id=workspace_id,
            databases=databases,
            default=default,
            enabled=enabled,
        )
        
        if not self.current_workspace:
            self.current_workspace = name
        
        logger.info(f"Added workspace: {name}")

    def remove_workspace(self, name: str):
        """
        Remove a workspace.

        Args:
            name: Workspace name to remove
        """
        if name not in self.workspaces:
            logger.warning(f"Workspace not found: {name}")
            return
        
        del self.workspaces[name]
        
        if self.current_workspace == name:
            self.current_workspace = None
            # Select new default
            for ws_name, ws in self.workspaces.items():
                if ws.default:
                    self.current_workspace = ws_name
                    break
        
        logger.info(f"Removed workspace: {name}")

    def select_workspace(self, name: str):
        """
        Select the current workspace.

        Args:
            name: Workspace name to select
        """
        if name not in self.workspaces:
            logger.error(f"Workspace not found: {name}")
            return False
        
        if not self.workspaces[name].enabled:
            logger.error(f"Workspace is disabled: {name}")
            return False
        
        self.current_workspace = name
        logger.info(f"Selected workspace: {name}")
        return True

    def get_current_workspace(self) -> Optional[WorkspaceConfig]:
        """Get the current workspace configuration."""
        if not self.current_workspace:
            return None
        return self.workspaces.get(self.current_workspace)

    def get_workspace(self, name: str) -> Optional[WorkspaceConfig]:
        """Get a specific workspace by name."""
        return self.workspaces.get(name)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces."""
        return [
            {
                "name": ws.name,
                "workspace_id": ws.workspace_id,
                "default": ws.default,
                "enabled": ws.enabled,
                "current": ws.name == self.current_workspace,
                "database_count": len(ws.databases),
            }
            for ws in self.workspaces.values()
        ]

    def get_database_id(self, database_name: str, workspace_name: Optional[str] = None) -> Optional[str]:
        """
        Get database ID for a given database name.

        Args:
            database_name: Name of the database
            workspace_name: Optional workspace name (uses current if not specified)

        Returns:
            Database ID or None
        """
        ws_name = workspace_name or self.current_workspace
        if not ws_name:
            return None
        
        ws = self.workspaces.get(ws_name)
        if not ws:
            return None
        
        return ws.databases.get(database_name)

    def set_database_id(
        self,
        database_name: str,
        database_id: str,
        workspace_name: Optional[str] = None,
    ):
        """
        Set database ID for a given database name.

        Args:
            database_name: Name of the database
            database_id: Database ID
            workspace_name: Optional workspace name
        """
        ws_name = workspace_name or self.current_workspace
        if not ws_name:
            logger.error("No workspace selected")
            return
        
        ws = self.workspaces.get(ws_name)
        if not ws:
            logger.error(f"Workspace not found: {ws_name}")
            return
        
        ws.databases[database_name] = database_id
        logger.info(f"Set {database_name} = {database_id} in {ws_name}")

    def get_all_database_ids(self, workspace_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get all database IDs for a workspace.

        Args:
            workspace_name: Optional workspace name

        Returns:
            Dictionary of database name -> ID
        """
        ws_name = workspace_name or self.current_workspace
        if not ws_name:
            return {}
        
        ws = self.workspaces.get(ws_name)
        if not ws:
            return {}
        
        return ws.databases

    def sync_to_all_workspaces(self, sync_function, *args, **kwargs) -> Dict[str, Any]:
        """
        Run sync function on all enabled workspaces.

        Args:
            sync_function: Function to call for each workspace
            *args: Arguments to pass to sync function
            **kwargs: Keyword arguments to pass to sync function

        Returns:
            Dictionary of workspace_name -> result
        """
        results = {}
        
        for name, ws in self.workspaces.items():
            if not ws.enabled:
                continue
            
            # Temporarily set workspace
            old_current = self.current_workspace
            self.current_workspace = name
            
            try:
                result = sync_function(*args, **kwargs)
                results[name] = {"success": True, "result": result}
            except Exception as e:
                results[name] = {"success": False, "error": str(e)}
            finally:
                self.current_workspace = old_current
        
        return results

    def export_config(self, output_file: str):
        """
        Export configuration to a file.

        Args:
            output_file: Path to export file
        """
        data = {
            "workspaces": [
                {
                    "name": ws.name,
                    "workspace_id": ws.workspace_id,
                    "databases": ws.databases,
                    "default": ws.default,
                }
                for ws in self.workspaces.values()
            ]
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported config to {output_file}")

    def import_config(self, input_file: str, merge: bool = False):
        """
        Import configuration from a file.

        Args:
            input_file: Path to import file
            merge: Whether to merge with existing config
        """
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not merge:
                self.workspaces.clear()
            
            for ws_data in data.get("workspaces", []):
                self.add_workspace(
                    name=ws_data["name"],
                    api_key=ws_data.get("api_key", ""),
                    workspace_id=ws_data["workspace_id"],
                    databases=ws_data.get("databases", {}),
                    default=ws_data.get("default", False),
                )
            
            logger.info(f"Imported config from {input_file}")
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
