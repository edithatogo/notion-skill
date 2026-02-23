"""
Notion API Client

Handles all interactions with the Notion API including:
- Creating/updating pages
- Managing database entries
- Batch operations for efficiency
"""

import os
import logging
from typing import Optional, Dict, List, Any
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for interacting with Notion API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Notion client.

        Args:
            api_key: Notion API key. If not provided, reads from NOTION_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        if not self.api_key:
            raise ValueError("Notion API key not provided")

        self.client = Client(auth=self.api_key)
        logger.info("Notion client initialized")

    def create_page(
        self,
        parent_database_id: str,
        properties: Dict[str, Any],
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new page in a Notion database.

        Args:
            parent_database_id: ID of the parent database
            properties: Page properties matching database schema
            children: Optional child blocks to add

        Returns:
            Created page object
        """
        try:
            page = self.client.pages.create(
                parent={"database_id": parent_database_id},
                properties=properties,
            )

            if children:
                self.client.blocks.children.append(
                    block_id=page["id"], children=children
                )

            logger.info(f"Created page in database {parent_database_id}")
            return page

        except APIResponseError as e:
            logger.error(f"Failed to create page: {e}")
            raise

    def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Notion page.

        Args:
            page_id: ID of the page to update
            properties: Properties to update
            children: Optional child blocks to append

        Returns:
            Updated page object
        """
        try:
            page = self.client.pages.update(
                page_id=page_id,
                properties=properties or {},
            )

            if children:
                self.client.blocks.children.append(
                    block_id=page_id, children=children
                )

            logger.info(f"Updated page {page_id}")
            return page

        except APIResponseError as e:
            logger.error(f"Failed to update page: {e}")
            raise

    def query_database(
        self,
        database_id: str,
        filter: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query a Notion database.

        Args:
            database_id: ID of the database to query
            filter: Optional filter criteria
            sorts: Optional sort criteria

        Returns:
            List of matching pages
        """
        try:
            results = []
            start_cursor = None

            while True:
                response = self.client.databases.query(
                    database_id=database_id,
                    filter=filter,
                    sorts=sorts,
                    start_cursor=start_cursor,
                )

                results.extend(response["results"])

                if not response.get("has_more"):
                    break

                start_cursor = response.get("next_cursor")

            logger.info(f"Queried database {database_id}, found {len(results)} results")
            return results

        except APIResponseError as e:
            logger.error(f"Failed to query database: {e}")
            raise

    def find_page_by_title(
        self, database_id: str, title: str, property_name: str = "Name"
    ) -> Optional[Dict[str, Any]]:
        """
        Find a page by its title property.

        Args:
            database_id: ID of the database to search
            title: Title to search for
            property_name: Name of the title property

        Returns:
            Page object if found, None otherwise
        """
        pages = self.query_database(
            database_id=database_id,
            filter={
                "property": property_name,
                "title": {"contains": title},
            },
        )

        if pages:
            return pages[0]
        return None

    def create_database_entry(
        self,
        database_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new entry in a Notion database.

        Args:
            database_id: ID of the database
            properties: Entry properties

        Returns:
            Created entry object
        """
        return self.create_page(
            parent_database_id=database_id,
            properties=properties,
        )

    def batch_update(
        self,
        updates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Batch update multiple pages.

        Args:
            updates: List of dicts with 'page_id' and 'properties'

        Returns:
            List of updated page objects
        """
        results = []
        for update in updates:
            try:
                page = self.update_page(
                    page_id=update["page_id"],
                    properties=update.get("properties", {}),
                )
                results.append(page)
            except APIResponseError as e:
                logger.error(f"Failed to update page {update['page_id']}: {e}")
                results.append(None)

        return results

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """
        Get database metadata.

        Args:
            database_id: ID of the database

        Returns:
            Database object
        """
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except APIResponseError as e:
            logger.error(f"Failed to get database: {e}")
            raise
