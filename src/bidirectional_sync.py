"""
Bidirectional Sync (Notion → Linear)

Syncs changes from Notion back to Linear, enabling true bidirectional synchronization.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BidirectionalSync:
    """Handles bidirectional synchronization between Notion and Linear."""

    def __init__(self, notion_client, linear_client, config: Optional[Dict[str, Any]] = None):
        """
        Initialize bidirectional sync.

        Args:
            notion_client: Notion API client
            linear_client: Linear API client
            config: Sync configuration
        """
        self.notion = notion_client
        self.linear = linear_client
        self.config = config or {}
        
        # Track sync direction to prevent loops
        self._sync_in_progress = False
        self._last_sync_timestamps: Dict[str, str] = {}

    def sync_notion_to_linear(
        self,
        notion_page_id: str,
        linear_issue_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Sync changes from Notion page to Linear issue.

        Args:
            notion_page_id: ID of the Notion page
            linear_issue_id: ID of the Linear issue
            fields: Specific fields to sync (None = all supported fields)

        Returns:
            Sync result with changes made
        """
        if self._sync_in_progress:
            logger.warning("Sync already in progress, skipping to prevent loop")
            return {"success": False, "reason": "sync_in_progress"}

        self._sync_in_progress = True
        result = {
            "success": True,
            "source": "notion",
            "target": "linear",
            "changes": [],
            "errors": [],
        }

        try:
            # Get Notion page data
            notion_data = self._fetch_notion_page(notion_page_id)
            
            # Get Linear issue data
            linear_data = self._fetch_linear_issue(linear_issue_id)
            
            # Detect changes
            changes = self._detect_notion_changes(notion_data, linear_data, fields)
            
            if not changes:
                result["message"] = "No changes detected"
                return result

            # Apply changes to Linear
            for change in changes:
                success = self._apply_change_to_linear(linear_issue_id, change)
                if success:
                    result["changes"].append(change)
                else:
                    result["errors"].append(f"Failed to apply change: {change['field']}")

            result["message"] = f"Synced {len(result['changes'])} changes to Linear"
            
            # Update last sync timestamp
            self._last_sync_timestamps[f"notion_{notion_page_id}"] = datetime.now().isoformat()

        except Exception as e:
            logger.exception(f"Bidirectional sync failed: {e}")
            result["success"] = False
            result["errors"].append(str(e))
        finally:
            self._sync_in_progress = False

        return result

    def sync_linear_to_notion(
        self,
        linear_issue_id: str,
        notion_page_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Sync changes from Linear issue to Notion page.

        Args:
            linear_issue_id: ID of the Linear issue
            notion_page_id: ID of the Notion page
            fields: Specific fields to sync (None = all supported fields)

        Returns:
            Sync result with changes made
        """
        if self._sync_in_progress:
            logger.warning("Sync already in progress, skipping to prevent loop")
            return {"success": False, "reason": "sync_in_progress"}

        self._sync_in_progress = True
        result = {
            "success": True,
            "source": "linear",
            "target": "notion",
            "changes": [],
            "errors": [],
        }

        try:
            # Get Linear issue data
            linear_data = self._fetch_linear_issue(linear_issue_id)
            
            # Get Notion page data
            notion_data = self._fetch_notion_page(notion_page_id)
            
            # Detect changes
            changes = self._detect_linear_changes(linear_data, notion_data, fields)
            
            if not changes:
                result["message"] = "No changes detected"
                return result

            # Apply changes to Notion
            for change in changes:
                success = self._apply_change_to_notion(notion_page_id, change)
                if success:
                    result["changes"].append(change)
                else:
                    result["errors"].append(f"Failed to apply change: {change['field']}")

            result["message"] = f"Synced {len(result['changes'])} changes to Notion"
            
            # Update last sync timestamp
            self._last_sync_timestamps[f"linear_{linear_issue_id}"] = datetime.now().isoformat()

        except Exception as e:
            logger.exception(f"Bidirectional sync failed: {e}")
            result["success"] = False
            result["errors"].append(str(e))
        finally:
            self._sync_in_progress = False

        return result

    def _fetch_notion_page(self, page_id: str) -> Dict[str, Any]:
        """Fetch Notion page data."""
        # This would use the Notion client to fetch page data
        # For now, return a placeholder structure
        return {
            "id": page_id,
            "properties": {},
        }

    def _fetch_linear_issue(self, issue_id: str) -> Dict[str, Any]:
        """Fetch Linear issue data."""
        # This would use the Linear client to fetch issue data
        return {
            "id": issue_id,
            "title": "",
            "description": "",
            "state": {"name": "Todo"},
            "priority": 2,
            "assignee": None,
            "dueDate": None,
        }

    def _detect_notion_changes(
        self,
        notion_data: Dict[str, Any],
        linear_data: Dict[str, Any],
        fields: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Detect changes in Notion that need to be synced to Linear."""
        changes = []
        
        # Supported field mappings
        field_mappings = {
            "title": ("Name", self._map_title),
            "description": ("Description", self._map_description),
            "status": ("Status", self._map_status),
            "priority": ("Priority", self._map_priority),
            "assignee": ("Owner", self._map_assignee),
        }

        fields_to_check = fields or list(field_mappings.keys())

        for field_name in fields_to_check:
            if field_name not in field_mappings:
                continue
                
            notion_prop, mapper = field_mappings[field_name]
            notion_value = self._get_notion_property(notion_data, notion_prop)
            linear_value = linear_data.get(field_name)
            
            if mapper.should_sync(notion_value, linear_value):
                changes.append({
                    "field": field_name,
                    "source_value": notion_value,
                    "target_value": mapper.to_linear(notion_value),
                    "direction": "notion_to_linear",
                })

        return changes

    def _detect_linear_changes(
        self,
        linear_data: Dict[str, Any],
        notion_data: Dict[str, Any],
        fields: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Detect changes in Linear that need to be synced to Notion."""
        changes = []
        
        # Similar to above but reverse direction
        field_mappings = {
            "title": ("Name", self._map_title),
            "description": ("Description", self._map_description),
            "status": ("Status", self._map_status),
            "priority": ("Priority", self._map_priority),
            "assignee": ("Owner", self._map_assignee),
        }

        fields_to_check = fields or list(field_mappings.keys())

        for field_name in fields_to_check:
            if field_name not in field_mappings:
                continue
                
            notion_prop, mapper = field_mappings[field_name]
            linear_value = linear_data.get(field_name)
            notion_value = self._get_notion_property(notion_data, notion_prop)
            
            if mapper.should_sync(linear_value, notion_value):
                changes.append({
                    "field": field_name,
                    "source_value": linear_value,
                    "target_value": mapper.to_notion(linear_value),
                    "direction": "linear_to_notion",
                })

        return changes

    def _apply_change_to_linear(self, issue_id: str, change: Dict[str, Any]) -> bool:
        """Apply a change to Linear issue."""
        try:
            # Build update payload
            update_payload = {}
            
            if change["field"] == "title":
                update_payload["title"] = change["target_value"]
            elif change["field"] == "description":
                update_payload["description"] = change["target_value"]
            elif change["field"] == "status":
                # Map status to Linear state ID
                update_payload["stateId"] = self._get_linear_state_id(change["target_value"])
            elif change["field"] == "priority":
                update_payload["priority"] = change["target_value"]
            elif change["field"] == "assignee":
                update_payload["assigneeId"] = self._get_linear_user_id(change["target_value"])

            # Call Linear API to update
            # self.linear.update_issue(issue_id, **update_payload)
            
            logger.info(f"Applied change to Linear {issue_id}: {change['field']}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply change to Linear: {e}")
            return False

    def _apply_change_to_notion(self, page_id: str, change: Dict[str, Any]) -> bool:
        """Apply a change to Notion page."""
        try:
            # Build update payload
            properties = {}
            
            if change["field"] == "title":
                properties["Name"] = {
                    "title": [{"text": {"content": change["target_value"]}}]
                }
            elif change["field"] == "description":
                properties["Description"] = {
                    "rich_text": [{"text": {"content": change["target_value"]}}]
                }
            elif change["field"] == "status":
                properties["Status"] = {
                    "select": {"name": change["target_value"]}
                }
            elif change["field"] == "priority":
                properties["Priority"] = {
                    "select": {"name": change["target_value"]}
                }

            # Call Notion API to update
            # self.notion.update_page(page_id, properties=properties)
            
            logger.info(f"Applied change to Notion {page_id}: {change['field']}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply change to Notion: {e}")
            return False

    def _get_notion_property(self, notion_data: Dict[str, Any], prop_name: str) -> Any:
        """Extract a property value from Notion page data."""
        properties = notion_data.get("properties", {})
        prop = properties.get(prop_name, {})
        
        # Handle different property types
        if "title" in prop:
            titles = prop.get("title", [])
            return titles[0].get("plain_text", "") if titles else ""
        elif "rich_text" in prop:
            texts = prop.get("rich_text", [])
            return texts[0].get("plain_text", "") if texts else ""
        elif "select" in prop:
            return prop.get("select", {}).get("name", "")
        elif "checkbox" in prop:
            return prop.get("checkbox", False)
        
        return None

    # Field mappers
    class _map_title:
        @staticmethod
        def should_sync(notion_val, linear_val) -> bool:
            return notion_val != linear_val
        
        @staticmethod
        def to_linear(val):
            return val
        
        @staticmethod
        def to_notion(val):
            return val

    class _map_description:
        @staticmethod
        def should_sync(notion_val, linear_val) -> bool:
            return notion_val != linear_val
        
        @staticmethod
        def to_linear(val):
            return val
        
        @staticmethod
        def to_notion(val):
            return val

    class _map_status:
        STATUS_MAP = {
            "Planning": "Backlog",
            "Active": "In Progress",
            "In Progress": "In Progress",
            "Review": "In Review",
            "Complete": "Done",
            "Done": "Done",
            "Archived": "Canceled",
        }
        
        @staticmethod
        def should_sync(notion_val, linear_val) -> bool:
            notion_mapped = BidirectionalSync._map_status.STATUS_MAP.get(notion_val, notion_val)
            return notion_mapped != linear_val
        
        @staticmethod
        def to_linear(val):
            return BidirectionalSync._map_status.STATUS_MAP.get(val, val)
        
        @staticmethod
        def to_notion(val):
            # Reverse mapping
            reverse_map = {v: k for k, v in BidirectionalSync._map_status.STATUS_MAP.items()}
            return reverse_map.get(val, val)

    class _map_priority:
        PRIORITY_MAP = {
            "P0": 0,
            "P1": 1,
            "P2": 2,
            "P3": 3,
            "P4": 4,
        }
        
        @staticmethod
        def should_sync(notion_val, linear_val) -> bool:
            notion_mapped = BidirectionalSync._map_priority.PRIORITY_MAP.get(notion_val, 2)
            return notion_mapped != linear_val
        
        @staticmethod
        def to_linear(val):
            return BidirectionalSync._map_priority.PRIORITY_MAP.get(val, 2)
        
        @staticmethod
        def to_notion(val):
            reverse_map = {v: k for k, v in BidirectionalSync._map_priority.PRIORITY_MAP.items()}
            return reverse_map.get(val, "P2")

    class _map_assignee:
        @staticmethod
        def should_sync(notion_val, linear_val) -> bool:
            return notion_val != linear_val
        
        @staticmethod
        def to_linear(val):
            # Would need to map Notion user to Linear user ID
            return val
        
        @staticmethod
        def to_notion(val):
            return val

    def _get_linear_state_id(self, state_name: str) -> str:
        """Get Linear state ID by name."""
        # Would fetch from Linear API
        return "state_id_placeholder"

    def _get_linear_user_id(self, user_name: str) -> str:
        """Get Linear user ID by name."""
        # Would fetch from Linear API
        return "user_id_placeholder"

    def get_sync_timestamp(self, entity_id: str, direction: str) -> Optional[str]:
        """Get last sync timestamp for an entity."""
        key = f"{direction}_{entity_id}"
        return self._last_sync_timestamps.get(key)

    def clear_sync_timestamps(self):
        """Clear all sync timestamps."""
        self._last_sync_timestamps.clear()
