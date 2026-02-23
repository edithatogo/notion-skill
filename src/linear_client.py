"""
Linear API Client

Handles all interactions with Linear API including:
- Fetching projects and issues
- Querying cycles and milestones
- GraphQL API for advanced queries
"""

import os
import logging
from typing import Optional, Dict, List, Any
import requests

logger = logging.getLogger(__name__)


class LinearClient:
    """Client for interacting with Linear API."""

    API_ENDPOINT = "https://api.linearhq.com/graphql"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Linear client.

        Args:
            api_key: Linear API key. If not provided, reads from LINEAR_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError("Linear API key not provided")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        logger.info("Linear client initialized")

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Query response data
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(self.API_ENDPOINT, json=payload)
            response.raise_for_status()

            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data.get("data", {})

        except requests.RequestException as e:
            logger.error(f"Failed to execute query: {e}")
            raise

    def get_projects(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all projects for a team.

        Args:
            team_id: Optional team ID to filter by

        Returns:
            List of projects
        """
        query = """
        query GetProjects($teamId: String) {
            projects(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                    description
                    state
                    createdAt
                    updatedAt
                    startDate
                    targetDate
                    priority
                    team {
                        id
                        name
                    }
                }
            }
        }
        """

        variables = {"teamId": team_id} if team_id else {}
        data = self.execute_query(query, variables)
        return data.get("projects", {}).get("nodes", [])

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project object or None
        """
        query = """
        query GetProject($id: ID!) {
            project(id: $id) {
                id
                name
                description
                state
                createdAt
                updatedAt
                startDate
                targetDate
                priority
                team {
                    id
                    name
                }
            }
        }
        """

        data = self.execute_query(query, {"id": project_id})
        return data.get("project")

    def get_issues(self, project_id: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get issues for a project or team.

        Args:
            project_id: Optional project ID to filter by
            team_id: Optional team ID to filter by

        Returns:
            List of issues
        """
        query = """
        query GetIssues($projectId: String, $teamId: String) {
            issues(
                filter: {
                    project: { id: { eq: $projectId } }
                    team: { id: { eq: $teamId } }
                }
            ) {
                nodes {
                    id
                    title
                    description
                    state {
                        id
                        name
                        type
                        color
                    }
                    priority
                    assignee {
                        id
                        name
                        email
                    }
                    createdAt
                    updatedAt
                    completedAt
                    project {
                        id
                        name
                    }
                    team {
                        id
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        variables = {}
        if project_id:
            variables["projectId"] = project_id
        if team_id:
            variables["teamId"] = team_id

        data = self.execute_query(query, variables)
        return data.get("issues", {}).get("nodes", [])

    def get_cycles(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get cycles for a team.

        Args:
            team_id: Team ID

        Returns:
            List of cycles
        """
        query = """
        query GetCycles($teamId: String!) {
            cycles(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                    number
                    startDate
                    endDate
                    createdAt
                    updatedAt
                }
            }
        }
        """

        data = self.execute_query(query, {"teamId": team_id})
        return data.get("cycles", {}).get("nodes", [])

    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all teams.

        Returns:
            List of teams
        """
        query = """
        query GetTeams {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """

        data = self.execute_query(query)
        return data.get("teams", {}).get("nodes", [])

    def search_projects(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Search projects by name.

        Args:
            query_text: Search query

        Returns:
            List of matching projects
        """
        projects = self.get_projects()
        return [
            p for p in projects
            if query_text.lower() in p.get("name", "").lower()
            or (p.get("description") and query_text.lower() in p.get("description", "").lower())
        ]
