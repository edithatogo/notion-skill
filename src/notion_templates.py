"""
Notion Database Templates

Provides templates for creating standardized Notion databases.
"""

from typing import Dict, Any, List, Optional


# Repository Database Template
REPOSITORY_DATABASE_TEMPLATE: Dict[str, Any] = {
    "title": [{"text": {"content": "Repositories"}}],
    "properties": {
        "Name": {
            "title": {}
        },
        "Description": {
            "rich_text": {}
        },
        "Path": {
            "rich_text": {}
        },
        "Primary Language": {
            "select": {
                "options": [
                    {"name": "Python", "color": "blue"},
                    {"name": "JavaScript", "color": "yellow"},
                    {"name": "TypeScript", "color": "blue"},
                    {"name": "Java", "color": "red"},
                    {"name": "Go", "color": "blue"},
                    {"name": "Rust", "color": "orange"},
                    {"name": "Ruby", "color": "red"},
                    {"name": "PHP", "color": "purple"},
                    {"name": "C++", "color": "blue"},
                    {"name": "C#", "color": "purple"},
                    {"name": "Swift", "color": "orange"},
                    {"name": "Kotlin", "color": "purple"},
                    {"name": "Scala", "color": "red"},
                    {"name": "Shell", "color": "gray"},
                    {"name": "Markdown", "color": "blue"},
                    {"name": "Other", "color": "gray"},
                ]
            }
        },
        "Last Commit": {
            "date": {}
        },
        "Last Commit Author": {
            "rich_text": {}
        },
        "Last Commit Message": {
            "rich_text": {}
        },
        "Has Conductor": {
            "checkbox": {}
        },
        "Track Count": {
            "number": {
                "format": "number"
            }
        },
        "Linear Project": {
            "relation": {}
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Active", "color": "green"},
                    {"name": "At Risk", "color": "yellow"},
                    {"name": "Blocked", "color": "red"},
                    {"name": "Archived", "color": "gray"},
                    {"name": "Complete", "color": "blue"},
                ]
            }
        },
        "Priority": {
            "select": {
                "options": [
                    {"name": "P0", "color": "red"},
                    {"name": "P1", "color": "orange"},
                    {"name": "P2", "color": "yellow"},
                    {"name": "P3", "color": "blue"},
                ]
            }
        },
        "Team": {
            "multi_select": {
                "options": [
                    {"name": "Engineering", "color": "blue"},
                    {"name": "Research", "color": "green"},
                    {"name": "Product", "color": "purple"},
                    {"name": "Data", "color": "orange"},
                ]
            }
        },
        "Sync Enabled": {
            "checkbox": {}
        },
        "Last Synced": {
            "date": {}
        },
        "URL": {
            "url": {}
        },
        "Tags": {
            "multi_select": {
                "options": [
                    {"name": "Skill", "color": "blue"},
                    {"name": "Plugin", "color": "green"},
                    {"name": "Tool", "color": "purple"},
                    {"name": "Library", "color": "orange"},
                    {"name": "MCP", "color": "pink"},
                ]
            }
        },
    }
}

# Tracks Database Template
TRACKS_DATABASE_TEMPLATE: Dict[str, Any] = {
    "title": [{"text": {"content": "Tracks"}}],
    "properties": {
        "Track Name": {
            "title": {}
        },
        "Repository": {
            "relation": {}
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Planning", "color": "gray"},
                    {"name": "Active", "color": "yellow"},
                    {"name": "In Progress", "color": "blue"},
                    {"name": "Review", "color": "orange"},
                    {"name": "Complete", "color": "green"},
                    {"name": "Archived", "color": "default"},
                    {"name": "Blocked", "color": "red"},
                ]
            }
        },
        "Priority": {
            "select": {
                "options": [
                    {"name": "P0", "color": "red"},
                    {"name": "P1", "color": "orange"},
                    {"name": "P2", "color": "yellow"},
                    {"name": "P3", "color": "blue"},
                ]
            }
        },
        "Phase": {
            "number": {
                "format": "number"
            }
        },
        "Commit SHA": {
            "rich_text": {}
        },
        "Completed Date": {
            "date": {}
        },
        "Linear Issues": {
            "relation": {}
        },
        "Archive Path": {
            "url": {}
        },
        "Dependencies": {
            "relation": {}
        },
        "Owner": {
            "people": {}
        },
        "Estimate (days)": {
            "number": {
                "format": "number"
            }
        },
        "Actual (days)": {
            "number": {
                "format": "number"
            }
        },
        "Artifacts": {
            "rich_text": {}
        },
        "Notes": {
            "rich_text": {}
        },
    }
}

# Linear Projects Database Template
LINEAR_PROJECTS_DATABASE_TEMPLATE: Dict[str, Any] = {
    "title": [{"text": {"content": "Linear Projects"}}],
    "properties": {
        "Project Name": {
            "title": {}
        },
        "Linear URL": {
            "url": {}
        },
        "Status": {
            "select": {
                "options": [
                    {"name": "Backlog", "color": "gray"},
                    {"name": "Active", "color": "blue"},
                    {"name": "At Risk", "color": "yellow"},
                    {"name": "Complete", "color": "green"},
                    {"name": "Archived", "color": "default"},
                ]
            }
        },
        "Team": {
            "select": {
                "options": [
                    {"name": "Edithatogo", "color": "blue"},
                    {"name": "Engineering", "color": "green"},
                    {"name": "Research", "color": "purple"},
                ]
            }
        },
        "Issue Count": {
            "number": {
                "format": "number"
            }
        },
        "Completed Issues": {
            "number": {
                "format": "number"
            }
        },
        "Progress (%)": {
            "rollup": {
                "relation_property": "Linear Issues",
                "rollup_property": "Status",
                "function": "percent_per_group"
            }
        },
        "Start Date": {
            "date": {}
        },
        "Target Date": {
            "date": {}
        },
        "Repository": {
            "relation": {}
        },
        "Last Updated": {
            "last_edited_time": {}
        },
        "Priority": {
            "select": {
                "options": [
                    {"name": "Urgent", "color": "red"},
                    {"name": "High", "color": "orange"},
                    {"name": "Medium", "color": "yellow"},
                    {"name": "Low", "color": "blue"},
                ]
            }
        },
    }
}

# Sync Metrics Database Template
SYNC_METRICS_DATABASE_TEMPLATE: Dict[str, Any] = {
    "title": [{"text": {"content": "Sync Metrics"}}],
    "properties": {
        "Sync ID": {
            "title": {}
        },
        "Repository": {
            "relation": {}
        },
        "Timestamp": {
            "date": {}
        },
        "Duration (ms)": {
            "number": {
                "format": "number"
            }
        },
        "Items Synced": {
            "number": {
                "format": "number"
            }
        },
        "API Calls Made": {
            "number": {
                "format": "number"
            }
        },
        "Rate Limit Hits": {
            "number": {
                "format": "number"
            }
        },
        "Errors Count": {
            "number": {
                "format": "number"
            }
        },
        "Success Rate": {
            "number": {
                "format": "percent"
            }
        },
        "Sync Mode": {
            "select": {
                "options": [
                    {"name": "Full", "color": "blue"},
                    {"name": "Incremental", "color": "green"},
                    {"name": "Preview", "color": "gray"},
                ]
            }
        },
        "Changes Detected": {
            "rich_text": {}
        },
        "Skipped": {
            "checkbox": {}
        },
        "Skip Reason": {
            "rich_text": {}
        },
    }
}


def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a database template by name.

    Args:
        template_name: Name of the template

    Returns:
        Template dictionary or None if not found
    """
    templates = {
        "repositories": REPOSITORY_DATABASE_TEMPLATE,
        "tracks": TRACKS_DATABASE_TEMPLATE,
        "linear_projects": LINEAR_PROJECTS_DATABASE_TEMPLATE,
        "sync_metrics": SYNC_METRICS_DATABASE_TEMPLATE,
    }
    return templates.get(template_name)


def get_all_templates() -> Dict[str, Dict[str, Any]]:
    """Get all available templates."""
    return {
        "repositories": REPOSITORY_DATABASE_TEMPLATE,
        "tracks": TRACKS_DATABASE_TEMPLATE,
        "linear_projects": LINEAR_PROJECTS_DATABASE_TEMPLATE,
        "sync_metrics": SYNC_METRICS_DATABASE_TEMPLATE,
    }


def create_database_payload(
    parent_page_id: str,
    template_name: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a payload for creating a Notion database.

    Args:
        parent_page_id: ID of the parent page
        template_name: Name of the template to use
        title: Optional custom title

    Returns:
        Payload for Notion API
    """
    template = get_template(template_name)
    if not template:
        raise ValueError(f"Unknown template: {template_name}")

    return {
        "parent": {"page_id": parent_page_id},
        "title": [{"text": {"content": title or template_name.title()}}],
        "properties": template["properties"],
    }
